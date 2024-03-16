"""
smswx.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, redirect, Blueprint
import csv, os, urllib, json

import config

bp = Blueprint('wx', __name__, '/wx')

##
## lib
##

def twiML(content):
    return twiResp(twiMsg(content))

def twiResp(content):
    """ Wrap content in a twiML Response tag"""
    resp = '<?xml version="1.0" encoding="UTF-8"?>'
    resp+= "<Response>"
    resp+= content
    resp+= "</Response>"
    return str(resp)

def twiMsg(msg, to=None):
    resp = '<Message'
    if to:
        resp += ' to="%s">'%to
    else:
        resp += '>'
    resp += msg
    resp += "</Message>"
    return str(resp)

def isfloat(s):
    try:
        float(s)
        return True
    except:
        return False


class TBError(Exception):
    msg = "TBError: '%s'"
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return self.msg % self.args

##
## geo
##
def coordsFromZip(zip, **kwargs):
    zipfile = os.path.join(config.DB_ROOT,"zipcode.csv")
    zipdb = csv.reader(open(zipfile))
    for row in zipdb:
        if len(row) and row[0]==zip:
            return row[3],row[4]
    raise LookupZipError(zip)


def coordsFromShelter(snam, **kwargs):
    sheltfile = os.path.join(config.DB_ROOT,"at_shelters.csv")
    sheltdb = csv.reader(open(sheltfile))
    maybes = []
    for row in sheltdb:
        if len(row) and snam.lower() in row[0].lower():
            maybes.append(row)
    if not len(maybes):
        raise LookupShelterError(snam)
    elif len(maybes) > 1:
        raise LookupMultipleError(snam, ','.join(m[0] for m in maybes))
    else:
        s = maybes[0]
        return s[30], s[31]

def coordsFromCitystate(citystate):
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
            citystate, [', '.join(r[0],r[2],r[1]) for r in maybes])
    return maybes[0][3], maybes[0][4],

##
## weatherbot
##

class LookupZipError(TBError):
    msg = "zip code not found: %s"
class LookupShelterError(TBError):
    msg = "Shelter name not found: %s"
class LookupLocationError(TBError):
    msg = "Location not found: %s"
class LookupMultipleError(TBError):
    msg = "multiple matches for %s: %s"

def wx_parse(wxjson, days=3):
    """Create a human-readable weather report from NWS JSON
    """
    if 'time' not in wxjson: return 'no data'
    labels = wxjson['time']['startPeriodName']

    rpt = "%s\n%s\n" % (
        wxjson['location']['areaDescription'],
        wxjson['creationDateLocal']
    )
    for i in range(days*2):
        rpt+="%s: %s \n\n" % (labels[i], wxjson['data']['text'][i])

    replaces = {'A chance of': 'Chance',
        ' percent':'%', 'around ': '~', ' to ': '-',
        'Southeast': 'SE', 'Northeast': 'NE', 
        'Southwest': 'SW', 'Northwest': 'NW',
        'East': 'E', 'West': 'W', 'South': 'S', 'North': 'N',
        'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
        'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 
        'Sunday': 'Sun', 'Night': 'PM',
        'thunderstorm': 't-storm', 'Chance of precipitation is': 'PoP'}
    for orig,new in replaces.items():
        rpt = rpt.replace(orig,new)

    return rpt[:1500]


def wx_by_lat_lon(lat, lon, **kwargs):
    urlbase = "http://forecast.weather.gov/MapClick.php"
    urlargs = dict(lat=lat,
                lon=lon,
                unit=0,     # imperial=0, metric=1
                lg="english", 
                FcstType="json")
    url = urlbase + "?" + urllib.parse.urlencode(urlargs)
    try:
        wxfd = urllib.request.urlopen(url)
        wxjson = json.load(wxfd)
        return wx_parse(wxjson, **kwargs)

    except urllib.error.URLError:
        return "NWS timed out looking for %s %s" % (lat, lon)

    except json.decoder.JSONDecodeError:
        return "no data for %s %s" % (lat, lon)




def wx(req):
    parts = req.split()
    if len(parts) < 1:
        return twiML("No args")
    elif len(parts)==1 and len(parts[0])==5 and parts[0].isdigit():
        lat,lon = coordsFromZip(req)
    elif len(parts) == 2 and isfloat(parts[0]) and isfloat(parts[1]):
        lat = parts[0]
        lon = parts[1]
    elif req.find(',') > -1:
        lat, lon = coordsFromCitystate(req)
    else:
        lat, lon = coordsFromShelter(req)

    return twiML(wx_by_lat_lon(lat,lon))

##
## status/registration
##


HANDLE_MIN = 2
HANDLE_MAX = 15
STATUS_MIN = 1
STATUS_MAX = 300

class AlreadySubscribedError(TBError):
    msg = "Already subscribed to @%s"
class NotSubscribedError(TBError):
    msg = "You're not subscribed to @%s"
class HandleTooLongError(TBError):
    msg = "Handle '@%s' is too long.  Max. "+str(HANDLE_MAX)+"  characters"
class HandleTooShortError(TBError):
    msg = "Handle '@%s' is too short.  Min. "+str(HANDLE_MIN)+" characters"
class HandleBadCharsError(TBError):
    msg = "Handle '@%s' is invalid. Letters and numbers only!"
class HandleExistsError(TBError):
    msg = "Handle '@%s' already exists"
class HandleUnknownError(TBError):
    msg = "I don't know any %s"
class NotRegisteredError(TBError):
    msg = "You must register a handle before you can do that. Text 'reg @handle' to register"
class StatusTooShortError(TBError):
    msg = "Status is too short. Min. "+str(STATUS_MIN)+" characters"
class StatusTooLongError(TBError):
    msg = "Status is too long. Max. "+str(STATUS_MAX)+" characters"

class User(object):
    # user data is stored in subdirectories of users
    # in files named phone@handle
    dbpath = os.path.join(config.DB_ROOT,'users')

    @classmethod
    def lookup(cls, crit):
        if crit.startswith('@'):
            fxn = lambda x: x.endswith(crit)
        else:
            fxn = lambda x: x.startswith(crit+'@')
        for f in os.listdir(cls.dbpath):
            if fxn(f):
                return cls(f)
        raise HandleUnknownError

    @classmethod
    def register(cls, phone, handle):
        if handle.startswith('@'):
            handle = handle.lstrip('@')
        if len(handle) > HANDLE_MAX:
            raise HandleTooLongError(handle)
        if len(handle) < HANDLE_MIN:
            raise HandleTooShortError(handle)
        if not handle.isalnum():
            raise HandleBadCharsError(handle)
        if cls.lookup('@'+handle):
            raise HandleExistsError(handle)

        userdir = '%s@%s' % (phone, handle)
        os.mkdir(os.path.join(cls.dbpath, userdir))
        return cls(userdir)

    def unregister(self):
        upath = os.path.join(self.dbpath,self.userdir)
        for f in os.listdir(upath):
            os.unlink(self.dbfile(f))
        os.rmdir(upath)

    def dbfile(self, fname):
        return os.path.join(self.dbpath, self.userdir, fname)

    def __init__(self, userdir):
        self.userdir = userdir
        self.phone, self.handle = userdir.split('@')
        try:
            self.status = open(self.dbfile('status')).read()
        except FileNotFoundError:
            self.status = None
        try:
            self.subs = open(self.dbfile('subs')).read().split('\n')
        except FileNotFoundError:
            self.subs = []
        self.save()

    def save(self):
        if '' in self.subs: self.subs.remove('')
        open(self.dbfile('subs'), 'w').write('\n'.join(self.subs))
        if self.status:
            open(self.dbfile('status'),'w').write(self.status)

    def subscribe(self, phone):
        if phone in self.subs:
            raise AlreadySubscribedError(handle)
        else:
            self.subs.append(phone)
        self.save()

    def unsubscribe(self, phone):
        if phone not in self.subs:
            raise NotSubscribedError(handle)
        else:
            self.subs.remove(phone)
        self.save()

    def setStatus(self, status):
        if len(status) > STATUS_MAX:
            raise StatusTooLongError
        if len(status) < STATUS_MIN:
            raise StatusTooShortError
        self.status = status
        self.save()


def status_update(user, status):
    user.setStatus(status)
    msgs = []
    tmpl = "@%s: %s" % (user.handle, status)
    for pnum in user.subs:
        msgs.append(twiMsg(tmpl, to=pnum))
    msgs.append(twiMsg("Success: update sent to %d followers" % len(msgs)))
    return twiResp(''.join(msgs))

##
## ui
##

@bp.route("/fetch")
def sms_reply():
    frm = request.args.get('From')
    sms = request.args.get('Body')
    if not frm or not sms:
        return twiML("No request")
    try:
        cmd,args = sms.split(maxsplit=1)
    except ValueError:
        cmd = sms
        args= ""

    try:
        if cmd in ('wx', 'weather'):
            return wx(args)
        elif cmd in ('register', 'reg'):
            u = User.register(frm, args)
            return twiML("Success:  @%s registered."%u.handle)
        elif cmd in ('unregister', 'unreg'):
            try:
                u = User.lookup(frm)
            except HandleUnknownError:
                raise NotRegisteredError
            u.unregister()
            return twiML("Success: @%s unregistered."%u.handle)
        elif cmd in ('subscribe', 'sub'):
            u = User.lookup(args)
            u.subscribe(frm)
            return twiML("Success: subscribed to @%s. Unsubscribe at any time by sending 'unsub @%s'" % (u.handle, u.handle))
        elif cmd in ('unsubscribe', 'unsub'):
            u = User.lookup(args)
            u.unsubscribe(frm)
            return twiML("Success: unsubscribed from @%s" % u.handle)
        elif cmd in ('status', 'st'):
            if args[0].startswith('@'):
                # this is a status request
                u = User.lookup(args)
                if u.status:
                    return twiML("@%s: %s" % (u.handle, u.status))
                else:
                    return twiML("No status for %s" % u.handle)
            else:
                # this is a status update
                u = User.lookup(frm)
                return status_update(u, args)

        elif cmd.startswith('@'):
            u = User.lookup(cmd)
            try:
                fu = User.lookup(frm)
                fh = fu.handle
            except HandleUnknownError:
                fh = frm
            msg = twiMsg('@'+fh+": "+args, to=u.phone)
            return twiResp(msg)
        else:
            return twiML("Unknown command %s.\n  To reply to a message, start your message with @handle, like this:\n @mg I hope you get the goat off the roof"" % cmd)

    except TBError as e:
        return twiML(str(e))


if __name__ == "__main__":
    app.run(debug=False)
