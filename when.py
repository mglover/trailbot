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
from datetime import datetime, timezone, timedelta

from .core import TBError, success, parseArgs
from .dispatch import TBRequest, tbroute, tbhelp
from .user import User, needsreg
from .userdata import UserObj
from .location import Location, areaCodeFromPhone,\
     LookupAreaCodeError, NotAnAreaCode

from .when_parser import WhenError, lexer, parser

UTC = timezone(timedelta(0))

class Zone(object):
    name = None
    source = None
    search = None
    tzinfo = None

    def __init__(self, name, source=None, search=None, tzinfo=None):
        self.name = name
        self.source = source
        self.search = search
        self.tzinfo = tzinfo

    @classmethod
    @property
    def default(cls):
        return cls(
            "UTC",
            source="default",
            search="default",
            tzinfo=UTC
        )

    @classmethod
    def fromLocation(cls, loc, source):
        assert type(loc) is Location
        zf = TimezoneFinder()
        return cls(
            zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat)),
            source=source,
            search=loc
        )

    @classmethod
    def fromName(cls, name):
        return cls(
            tzinfo = ZoneInfo(name),
            name = name,
            source = "ZoneInfo",
            search = name
        )

    @classmethod
    def fromRequest(cls, req):
        assert type(req) is TBRequest

        if req.user:
            zone = cls.fromUser(req.user)
            if zone.source != "default":
                return zone

        try:
            ac = areaCodeFromPhone(req.frm)
            loc = Location.fromAreaCode(ac, req.user)
        except (LookupAreaCodeError, NotAnAreaCode) as e:
           return cls.default

        return cls.fromLocation(loc, "phone")

    @classmethod
    def fromUser(cls, user):
        assert type(user) is User
        if user.tz:
            return cls.fromName(user.tz, source='user')

        loc = UserObj.lookup('here', requser=user)
        if loc:
            return cls.fromLocation(loc, "here")
        return cls.default

    @classmethod
    def fromArgs(cls, args):
        if args:
            loc = Location.fromInput(lnam, user)
            return cls.fromLocation(loc)
        return cls.default


class Clock(object):
    strip_fields = ('second', 'microsecond')
    def __init__(self, dt, tzinfo=None):
        assert type(dt) is datetime, dt
        if tzinfo:
            assert dt.tzinfo is None
            dt = dt.replace(tzinfo=tzinfo)
        else:
            assert dt.tzinfo is not None

        kvs = dict( [(k,0) for k in self.strip_fields ])
        self.dt = dt.replace(**kvs)

    @classmethod
    def now(self, zone):
        assert type(zone) is Zone, zone
        return cls(datetime.now(zone.tzinfo))


    def add(self, **kwargs):
        can_move = ('day', 'month', 'year')

        dt = self.dt

        if 'tzoffset' in kwargs:
            tzo = tzoffset(*kwargs['tzoffset'])
            dt = dt.astimezone(tzo)
            kwargs.pop('tzoffset')

        if 'year' in kwargs and kwargs['year'] < dt.year:
            raise WhenError("%d is in the past" % kwargs['year'])

        nxdt = dt + relativedelta(**kwargs)
        if nxdt >= dt:
            return nxdt

        moveable = [ p for p in can_move if p not in kwargs]
        for m in moveable:
            kk = { m: getattr(self.dt, m) + 1 }
            kk.update(kwargs)
            nxdt = dt + relativedelta(**kk)
            if nxdt >= dt:
                return nxdt

        raise StopIteration

    def inZone(self, tzinfo):
        return self.dt.astimezone(tzinfo)


class Event(object):
    def __init__(self, when, zone, stamps=None, created=None):
        self.when = when
        self.zone = zone
        self._rules = None
        self._repeats = False
        self._complete = False
        if not stamps:
            self.stamps = []
        self.created = created or datetime.now(UTC)
        self.rows = parser.parse(when, lexer=lexer)

    def __repr__(self):
        return "Event(%s, %s)" % (self.when, self.zone)

    def __eq__(self, other):
        assert type(other) is type(self)
        return self.when == other.when \
            and self.zone.name == other.zone.name

    @classmethod
    def fromDict(cls, d):
        zone = Zone.fromName(d['zone'])
        created = datetime.fromtimestamp(d['created'],
                tz=zone.tzinfo)
        return cls(
            d['when'],
            zone,
            created = created,
            stamps = d['stamps']
        )

    def toDict(self):
        if self._complete:
            return None

        return {
            'when':self.when,
            'zone': self.zone.name,
            'created': self.created.timestamp(),
            'stamps': self.stamps
        }

    def after(self, after):
        self._mkRules()
        return self._rules.after(after, inc=True)

    def is_active(self, after, before):
        assert type(after) is datetime, after
        assert type(before) is datetime, before
        self._mkRules()
        nxt = self._rules.after(after, inc=True)
        if nxt and nxt < before:
            return True
        return False

    def fire(self, ts):
        """This event has occured at the given timestamp"""
        self.stamps.append(ts)
        if not self._repeats and len(self.stamps) == len(self.rows):
            self._complete = True

    def _mkRules(self):
        if self._rules:
            return
        self._rules = rruleset(cache=True)

        clk = Clock(self.created)

        # either all rows will repeat, or no rows will
        for i in range(len(self.rows)):
            r = self.rows[i]
            if type(r) is tuple:
                self.repeats = True
                freq, kwargs = r
                start = kwargs.get('dtstart', {})
                kwargs['dtstart'] = clk.add(**start)
                if 'until' in kwargs:
                    kwargs['until'] = clk.add(**kwargs['until'])
                    #kwargs.pop('until')
                self._rules.rrule(rrule(freq, **kwargs))
            else:
                self._rules.rdate(clk.add(**r))

## TrailBot interface


@tbroute('when', cat="cal")
@tbhelp('''when -- parse a plain english date

say e.g: 'next tuesday'
or: 'every friday at 9am'
''')
def when(req):
    args = dict(parseArgs(req.args, ['in', 'is']))

    # query terms
    if 'is' in args:
        wh = args['is']
    else:
        wh = args['']

    # input and output timezones
    in_zone = Zone.fromRequest(req)
    if 'in' in args:
        out_zone = Zone.fromLocation(
                Location.fromInput(args['in'], req.user),
                source = 'args')
    else:
        out_zone = in_zone


    in_now = datetime.now(in_zone.tzinfo)
    evt = Event(wh, in_now.tzinfo)
    nxt = evt.after(in_now)

    if evt._repeats:
        msg = "%s is a recurring event. Next occurrence:" % (wh)
    else:
        msg = "%s is:" % (wh)

    msg += "\n%s %s" % (
        nxt.astimezone(out_zone.tzinfo).ctime(),
        out_zone.tzinfo)
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
    args = req.args.strip()
    if args:
        try:
            zone = Zone.fromName(req.args)
            req.user.tz = zone.name
        except (KeyError, ValueError):
            return "Not a valid time zone: %s" % req.args
        return success("Time zone set to %s" % req.user.tz)

    zone = getUserZone(req.user)

    if zone.source == "user":
        return "You have set your time zone to: %s" % zone.name
    if zone.source == "location":
        msg = "Based on your %s of: %s" % (loc.source, loc.orig)
        msg+= "\nyour time zone is %s" % zone
        return msg
    return "No time zone or current location set"


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
        loc = Location.fromInput(args.get('in'), requser=req.user)
        zone = Zone.fromLocation(loc, source='location')
    else:
        zone = getUserZone(req.user)
    now = datetime.now(zone.tzinfo)

    msg = "Current time is: %s" % now.ctime()
    msg+= "\nCurrent time zone is: %s" % zone.name
    if loc:
        msg+= "\n(Based on your %s of: %s)" % (loc.source, loc.orig)
    return msg


