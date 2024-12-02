__package__ = 'trailbot'

from dateutil.relativedelta import relativedelta, weekdays
from dateutil.rrule import rrule, rruleset,\
    YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY
from dateutil.tz import tzoffset

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:
    from backports.zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from datetime import datetime, timezone

from .core import TBError, success, parseArgs
from .dispatch import tbroute, tbhelp
from .user import needsreg
from .userdata import UserObj
from .location import Location, areaCodeFromPhone,\
     LookupAreaCodeError, NotAnAreaCode

zf = TimezoneFinder()

def getUserZone(user, default="UTC"):
    """ return the appropriate tz for the given User"""
    loc = None
    if user is not None:
        if user.tz:
            return (user.tz, None)

        loc = UserObj.lookup('here', requser=user)

    if not loc:
        try:
            ac = areaCodeFromPhone(user.phone)
            loc = Location.fromAreaCode(ac, user)
        except (LookupAreaCodeError, NotAnAreaCode) as e:
           loc = None

    if loc:
        zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
        return (zone, loc)

    return (default, None)


def getArgsZone(lnam, user):
    """ return appropriate tz given user args"""
    if lnam:
        loc = Location.fromInput(lnam, user)
        zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
        return zone, loc
    return None, None


def getReqNow(req):
    """ return the current time in the request's tz"""
    zone, _ = getUserZone(req.user)
    if zone:
        tzdata = ZoneInfo(zone)
    else:
        tzdata = timezone.utc
    return datetime.now(tzdata)


def mkdatetime(now, output_tz, kwargs):
    """ adjust now to UTC using desired offset (if given),
        zero-out second and microsecond
        apply the relativedelta in kwargs to the time
        and ensure it's not in the past
    """

    if 'tzoffset' in kwargs:
        input_tz = tzoffset(*kwargs['tzoffset'])
        kwargs.pop('tzoffset')
    else:
        input_tz = output_tz

    now = now.replace(second=0, microsecond=0).astimezone(input_tz)

    then = now + relativedelta(**kwargs)
    if then >= now: return then.astimezone(output_tz)

    if 'year' in kwargs and kwargs['year'] < now.year:
        raise WhenError("%d is in the past" % kwargs['year'])

    moveable = [ p for p in ('day', 'month', 'year') if p not in kwargs]
    for m in moveable:
        kk = { m: getattr(now, m) + 1 }
        kk.update(kwargs)
        then = now + relativedelta(**kk)
        if then >= now:
            return then.astimezone(output_tz)


def mkruleset(now, args):
    """ main interface to the parser
        given a timezone-aware datetime in now
        and a human-language date description in args
        return an rruleset representing the date(s)
    """
    tzinfo = now.tzinfo

    rows = parser.parse(args)
    rrs = rruleset()

    for r in rows:
        if type(r) is tuple:
            # this is an rrule
            freq, kwargs = r
            kwargs['dtstart'] = mkdatetime(now, tzinfo,
                kwargs.get('dtstart', {}))
            rrs.rrule(rrule(freq, **kwargs))
        else:
            kwargs = r
            rrs.rdate(mkdatetime(now, tzinfo, kwargs))
    return rrs



## TrailBot interface


@tbroute('when', cat="cal")
@tbhelp('''when -- parse a plain english date

say e.g: 'next tuesday'
or: 'every friday at 9am'
''')
def when(req):
    in_now = getReqNow(req)
    args = dict(parseArgs(req.args, ['max', 'in', 'is']))
    if 'is' in args:
        wh = args['is']
    else:
        wh = args['']
    zone, _ = getArgsZone(args.get('in'), user=req.user)
    if zone:
        out_now = datetime.now(ZoneInfo(zone))
    else:
        out_now = in_now
    try:
        max = int(args.get('max',3))
    except ValueError:
        pass

    rrs = mkruleset(in_now, wh)
    evts = [r for r in rrs.xafter(in_now, count=max)]
    if len(evts) == 1:
       msg = "%s is:" % (wh)
    else:
        msg = "%s is a recurring event. Next %d occurrences:" % (wh, len(evts))
    for e in evts:
        msg += "\n%s %s" % (e.astimezone(out_now.tzinfo).ctime(),
            out_now.tzinfo)
    return msg


@tbroute('tz', 'timezone', cat='cal')
@tbhelp('''tz -- set or get your time zone

say e.g.: 'tz America/New_York'
or: 'tz US/Eastern'
or just 'tz' to see the currently set zone

(if this isn't set, your current location (with 'here') will be used)
''')
@needsreg("to use time zones")
def tz(req):
    loc = None
    if not len(req.args.strip()):
        zone, loc = getUserZone(req.user)
        if zone is None:
            return "No time zone or current location set"
        elif loc is None:
            return "You have set your time zone to: %s" % zone
        else:
            msg = "Based on your %s of: %s" % (loc.source, loc.orig)
            msg+= "\nyour time zone is %s" % zone
            return msg
    try:
        req.user.tz = str(ZoneInfo(req.args))
    except (KeyError, ValueError):
        return "Not a valid time zone: %s" % req.args
    return success("Time zone set to %s" % req.user.tz)


@tbroute('untz', 'untimezone', cat='cal')
@tbhelp('''untz -- delete your time zone setting''')
@needsreg("to use time zones")
def untz(req):
    if not req.user.tz: return "No time zone set"
    req.user.tz = None
    return "Time zone deleted"


@tbroute('time', 'now', cat='cal')
@tbhelp('''now -- get current time in your timezone
see also: tz, here
''')
def now(req):
    args = dict(parseArgs(req.args, ['in']))
    if 'in' in args:
        zone, loc = getArgsZone(args.get('in'), user=req.user)
    else:
        zone, loc = getUserZone(req.user)
    now = datetime.now(tz=zone and ZoneInfo(zone))

    msg = "Current time is: %s" % now.ctime()
    msg+= "\nCurrent time zone is: %s" % zone
    if loc:
        msg+= "\n(Based on your %s of: %s)" % (loc.source, loc.orig)
    return msg


