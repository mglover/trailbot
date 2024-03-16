##
## geo
##
import json, os, csv

from . import config
from .core import TBError, proxy
from .user import UserObj

class LookupZipError(TBError):
    msg = "zip code not found: %s"
class LookupShelterError(TBError):
    msg = "Shelter name not found: %s"
class LookupLocationError(TBError):
    msg = "Location not found: %s"
class LookupMultipleError(TBError):
    msg = "multiple matches for %s: %s"

class SharingSpecError(TBError):
    msg = "Not a handle or '*': %s"

def isfloat(s):
    try:
        float(s)
        return True
    except:
        return False



class Location(UserObj):
    typ = 'loc'
    def __init__(self, lat, lon, orig=None, match=None):
        super().__init__()
        self.lat = lat
        self.lon = lon
        self.orig = orig
        self.match = match

    def __repr__(self):
        return str(self)

    def toDict(self):
        return {
            'lat':self.lat,
            'lon':self.lon,
            'orig':self.orig,
            'match':self.match
        }

    @classmethod
    def fromDict(cls, d):
        return cls(
            d['lat'],
            d['lon'],
            orig=d['orig'],
            match=d['match'],
        )

    def __str__(self):
        return "(%s,%s)" % (self.lat, self.lon)

    def toOSRM(self):
        return "%s,%s" % (self.lon, self.lat)

    def toSMS(self):
        return "%s\n(full name: %s)\ncoordinates: %s %s" % (
            self.orig, self.match, self.lat, self.lon)

    @classmethod
    def getDefault(cls):
        return 'here'

    @classmethod
    def fromZip(cls, zip):
        zipfile = os.path.join(config.DB_ROOT,"zipcode.csv")
        zipdb = csv.reader(open(zipfile))
        for row in zipdb:
            if len(row) and row[0]==zip:
                return cls(row[3], row[4], orig=zip)
        raise LookupZipError(zip)

    @classmethod
    def fromShelter(cls, snam):
        sheltfile = os.path.join(config.DB_ROOT,"at_shelters.csv")
        sheltdb = csv.reader(open(sheltfile))
        maybes = []
        for row in sheltdb:
            if len(row) and snam.lower() in row[0].lower():
                maybes.append(row)
        if not len(maybes):
            raise LookupShelterError(snam)
        elif len(maybes) > 1:
            raise LookupMultipleError(snam, ','.join(m[0] for m in 
                maybes))
        else:
            s = maybes[0]
        return cls(s[30], s[31], orig=snam)

    @classmethod
    def fromCitystate(cls, citystate):
        """look at a subset of the NGIS National File for place names
        """
        parts =citystate.split(',')
        if len(parts) == 3:
            city = parts[0].lstrip()
            county = parts[1].lstrip()
            state = parts[2].lstrip()
        elif len(parts) == 2:
            city = parts[0].lstrip()
            county = None
            state = parts[1].lstrip()
        else:
            raise LookupLocationError(citystate)

        maybes = []
        with open(os.path.join(config.DB_ROOT, "places.txt")) as plfd:
            pldb = csv.reader(plfd)
            for row in pldb:
                if not len(row):
                    continue
                if row[0].lower() == city.lower() \
                and row[1].lower() == state.lower() \
                and (not county or row[3].lower() == county.lower()):
                    maybes.append(row)


        if not len(maybes):
            raise LookupLocationError(citystate)
        if len(maybes) > 1:
            raise LookupMultipleError(
                citystate, [', '.join(r[0:2]) for r in maybes])
        return cls(maybes[0][3], maybes[0][4], orig=citystate)

    @classmethod
    def fromNominatim(cls, q):
        with proxy.get(
            'https://nominatim.openstreetmap.org/search',
            params= {"q":q, "format":"json"}
        ) as resp: data = resp.json()

        if not len(data):
            raise LookupLocationError(q)
        return cls(
             data[0]['lat'],
            data[0]['lon'],
            orig=q,
            match=data[0]["display_name"]
        )

    @classmethod
    def fromInput(cls, str, user=None):
        parts = str.split()

        if len(parts)==1:
            ud = cls.lookup(str.lower(), user)
            if ud: return ud
            if str.startswith('@'): raise LookupLocationError(str)
            if len(parts[0])==5 and parts[0].isdigit():
               return cls.fromZip(str)

        if len(parts) == 2 and \
            isfloat(parts[0]) and isfloat(parts[1]):
                return cls(parts[0], parts[1])

        if len(parts)>=2 and parts[-2].endswith(',') \
            and len(parts[-1].lstrip()) == 2:
            return cls.fromCitystate(str)

        if parts[0]=='trail:at':
            return cls.fromShelter(' '.join(parts[1:]))

        return cls.fromNominatim(str)

