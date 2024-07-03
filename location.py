## geo
##
import os, csv

from flask import render_template

from . import config
from .core import TBError
from .netsource import NetSource
from .userdata import UserObj
from .dispatch import tbroute, tbhelp

class LookupZipError(TBError):
    msg = "zip code not found: %s"
class LookupShelterError(TBError):
    msg = "Shelter name not found: %s"
class LookupLocationError(TBError):
    msg = "Location not found: %s"
class LookupMultipleError(TBError):
     msg = "%s"
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

    def __init__(self, lat=None, lon=None, orig=None, match=None, source=None,
            **kwargs):
        super().__init__(**kwargs)
        self.lat = lat
        self.lon = lon
        self.orig = orig
        self.match = match
        self.source = source

    def __repr__(self):
        return str(self)

    def toDict(self):
        return {
            'lat':self.lat,
            'lon':self.lon,
            'orig':self.orig,
            'match':self.match,
            'source': self.source
        }

    def parseData(self, d):
        self.lat = d.get('lat')
        self.lon = d.get('lon')
        self.orig = d.get('orig')
        self.match = d.get('match')
        self.source = d.get('source')
    def __str__(self):
        return "(%s,%s)" % (self.lat, self.lon)

    def toOSRM(self):
        return "%s,%s" % (self.lon, self.lat)

    def toSMS(self):
        return render_template("location.txt", obj=self)

    @classmethod
    def getDefault(cls):
        return 'here'

    @classmethod
    def fromZip(cls, zip, requser):
        zipfile = os.path.join(config.DB_ROOT,"zipcode.csv")
        with open(zipfile) as zipfd:
            zipdb = csv.reader(zipfd)
            for row in zipdb:
                if len(row) and row[0]==zip:
                    return cls(
                        lat=row[3],
                        lon = row[4],
                        orig = zip,
                        source = "ZIP code",
                        requser=requser
                    )
        raise LookupZipError(zip)

    @classmethod
    def fromShelter(cls, snam, requser):
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
        return cls(
            lat=s[30],
            lon=s[31],
            orig=snam,
            source = "AT shelter name",
            requser=requser
        )

    @classmethod
    def fromCitystate(cls, citystate, requser):
        """look at a subset of the NGIS National File for place names
        """
        parts = citystate.split(',')
        city = parts.pop(0).strip()
        if len(parts) > 1:
            county  = parts.pop(0).strip()
            if county.endswith(" county"):
                county = county[:-len(" county")]
        else:
            county = None
        state = parts.pop(0).strip()

        maybes = []
        plpath = os.path.join(config.DB_ROOT, "places.txt")
        with open(plpath, encoding="utf-8") as plfd:
            pldb = csv.reader(plfd)
            for row in pldb:
                if not len(row): continue
                if not row[0].lower() == city.lower(): continue
                if not row[1].lower() == state.lower(): continue
                if county and not row[2].lower() == county.lower(): continue
                maybes.append(row)

        if not len(maybes):
            raise LookupLocationError(citystate)
        if len(maybes) > 1:
            raise LookupMultipleError(render_template("location_multi.txt", 
                orig=citystate, rows=maybes))
        return cls(
            lat=maybes[0][3],
            lon=maybes[0][4],
            orig=citystate,
            source = "City/State",
            requser=requser
        )

    @classmethod
    def fromNominatim(cls, q, requser):
        class NominatimSource(NetSource):
            name = "Nominatim"
            baseUrl = 'https://nominatim.openstreetmap.org/search'
            def makeUrl(self, *args, **kwargs):
                return self.baseUrl

            def makeParams(self, q, *args, **kwargs):
                return {'q':q, 'format': 'json'}

        res = NominatimSource(q, raiseOnError=True)
        if not len(res.content):
            raise LookupLocationError(q)
        data = res.content[0]
        return cls(
            lat=data['lat'],
            lon=data['lon'],
            orig = data['display_name'],
            source = "Nominatim",
            requser=requser
        )


    @classmethod
    def fromInput(cls, str, requser):
        parts = str.split()
        if len(parts)==1:
            # saved location lookup
            ud = cls.lookup(str.lower(), requser)
            if ud: return ud
            if str.startswith('@'): raise LookupLocationError(str)
            if len(parts[0])==5 and parts[0].isdigit():
                return cls.fromZip(str, requser)

        elif len(parts) == 2 and \
            isfloat(parts[0]) and isfloat(parts[1]):
            return cls(
                lat=parts[0],
                lon=parts[1],
                orig=str,
                requser=requser,
                source = "Latitude/Longitude"
            )

        elif len(parts)>=2 and parts[-2].endswith(',') \
            and len(parts[-1].lstrip()) == 2:
            return cls.fromCitystate(str, requser)

        elif parts[0]=='trail:at':
            returncls.fromShelter(' '.join(parts[1:]), requser)

        return cls.fromNominatim(str, requser)
UserObj.register(Location)

@tbroute('where')
@tbhelp(
"""where -- lookup a location

You can say something like:
  'where Empire State Building'
  'where Denver, CO'
  'where Pinnacle Bank, Durango, Colorado'
""")
def where(req):
    loc = Location.fromInput(req.args, req.user)
    return loc.toSMS()


