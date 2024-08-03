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
class LookupAreaCodeError(TBError):
    msg = "Area code not found: %s"
class NotAnAreaCode(TBError):
    msg = "Not a US/Canada number: %s"
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

def geoFromCSV(file, key, latidx=1, lonidx=2):
    path = os.path.join(config.DB_ROOT, file)
    with open(path) as fd:
        db = csv.reader(fd)
        for row in db:
            if len(row) and row[0]==key:
                lat = row.pop(latidx)
                if lonidx > latidx: lonidx -= 1
                lon = row.pop(lonidx)
                row.pop(0)
                return lat, lon, row
        return None

def areaCodeFromPhone(phone, raiseOnFail=False):
    if not phone.startswith("+1"):
        if raiseOnFail: raise NotAnAreaCode(phone)
        return None
    return phone[2:5]

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
    def fromAreaCode(cls, ac, requser):
        geo = geoFromCSV("areacode.csv", ac, latidx=4, lonidx=5)
        if geo:
            return cls(
                lat = geo[0],
                lon = geo[1],
                orig = ac,
                match = ', '.join(geo[2]),
                source = "area code",
                requser=requser
            )
        raise LookupAreaCodeError(ac)

    @classmethod
    def fromZip(cls, zip, requser):
        geo = geoFromCSV("zipcode.csv", zip, latidx=3, lonidx=4)
        if geo:
            return cls(
                lat=geo[0],
                lon = geo[1],
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
            source = "city/state",
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
            source = "nominatim location",
            requser=requser
        )

    @classmethod
    def fromInput(cls, str, requser):
        cparts = str.split(',')
        sparts = str.split()

        if sparts[0]=='trail:at':
            # AT trail shelter name
            return cls.fromShelter(' '.join(parts[1:]), requser)

        if len(cparts)==1 and len(sparts)==1:
            #  zip, phone number, or saved addr
            if len(str)==5 and str.isdigit():
                return cls.fromZip(str, requser)
            elif len(str)==3 and str.isdigit():
                return cls.fromAreaCode(str, requser)

            ud = cls.lookup(str.lower(), requser)
            if ud: return ud
            if str.startswith('@'): raise LookupLocationError(str)

        elif len(cparts)==1 and len(sparts)==2 \
            and isfloat(sparts[0]) and isfloat(sparts[1]):
            # lat/lon pair
            return cls(
                lat=sparts[0],
                lon=sparts[1],
                orig=str,
                requser=requser,
                source="latitude/longitude"
            )

        elif len(cparts)>=2 and len(cparts[-1].lstrip()) == 2:
            # maybe a city/state pair
            return cls.fromCitystate(str, requser)

        # defailt: check nominatim
        return cls.fromNominatim(str, requser)

UserObj.register(Location)

@tbroute('where', cat='nav')
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


