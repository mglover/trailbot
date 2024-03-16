##
## geo
##
from urllib.request import Request, urlopen
from urllib.parse import urlencode
import json, os, csv

import config
from core import *

class LookupZipError(TBError):
    msg = "zip code not found: %s"
class LookupShelterError(TBError):
    msg = "Shelter name not found: %s"
class LookupLocationError(TBError):
    msg = "Location not found: %s"
class LookupMultipleError(TBError):
    msg = "multiple matches for %s: %s"


def isfloat(s):
    try:
        float(s)
        return True
    except:
        return False


class Location(object):
    def __init__(self, lat, lon, orig=None, match=None):
        self.lat = lat
        self.lon = lon
        self.orig = orig
        self.match = match

    def __str__(self):
        return "%s %s" % (self.lat, self.lon)

    def toOSRM(self):
        return "%s,%s" % (self.lon, self.lat)

    def toSMS(self):
        return "Location %s\nhas coordinates %s %s" % (
            self.orig, self.lat, self.lon) 

    def toJson(self):
        return json.dumps({
            'lat':self.lat,
            'lon':self.lon,
            'orig':self.orig,
            'match':self.match
        })

    @classmethod
    def fromJson(cls, json):
        d = json.loads(json)
        return cls(
            d['lat'],
            d['lon'],
            orig=d['orig'],
            match=d['match']
        )

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
        placefile = os.path.join(config.DB_ROOT, "places.txt")
        pldb = csv.reader(open(placefile))
        maybes = []
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

        for row in pldb:
            if not len(row): continue
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
        host="https://nominatim.openstreetmap.org"
        path="/search"
        query = urlencode({"q":q, "format":"json"})
        req = Request(
            "%s%s?%s" % (host, path, query),
            headers={"User-Agent": "TrailBot 1.3"}
        )
        resp = urlopen(req)
        data = json.load(resp)
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
        if user:
            data = user.getData('location', str)
        else:
            data = None

        if data:
            return cls.fromJson(data)

        elif len(parts)==1 \
            and len(parts[0])==5 and parts[0].isdigit():
            return cls.fromZip(str)

        elif len(parts) == 2 and \
            isfloat(parts[0]) and isfloat(parts[1]):
                return cls(parts[0], parts[1])
        elif str.find(',') > -1:
            return cls.fromCitystate(str)
        elif parts[0]=='trail:at':
            return cls.fromShelter(' '.join(parts[1:]))
        else:
            return cls.fromNominatim(str)

