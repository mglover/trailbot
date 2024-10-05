__package__ = 'trailbot'

import logging, time
from .pkgs.ply import lex, yacc
from .config import DEBUG
from .core import TBError


class WhenError(TBError):
    msg = "When? %s"

if DEBUG:
    logging.basicConfig(
        level = logging.DEBUG,
        filename = "errors.txt",
        filemode = "w",
        format = "%(lineno)4d:%(message)s"
    )
    log = logging.getLogger()
else:
    log = None


## -- setup the symbol table


tokmap = {}
units = ['MINUTE', 'HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR']
for u in units:
    tokmap[u] = ('UNIT', u)
    tokmap[u+'S'] = ('UNIT', u)

months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL',
         'MAY', 'JUNE', 'JULY', 'AUGUST',
         'SEPTEMBER','OCTOBER','NOVEMBER', 'DECEMBER']
i=1
for m in months:
    tokmap[m] = ('MONTH', m, i)
    tokmap[m[:3]] = ('MONTH', m, i)
    i += 1
tokmap['SEPT'] = ('MONTH', 'SEPTEMBER', 9)


days = ['MON', 'TUES', 'WEDNES', 'THURS', 'FRI', 'SATUR', 'SUN']
i=0
for d in days:
    v = ('DOW', d,  i)
    tokmap[d] = v
    tokmap[d+'DAY'] = v
    tokmap[d[:3]] = v
    tokmap[d[:2]] = v
    tokmap[d+'DAYS'] = ('DOWS', d, i)
    i += 1
tokmap['THUR'] = ('DOW', 'THURS', 4)

tzones = {'EST': -5*3600, 'CST': -6*3600, 'MST': -7*3600, 'PST': -8*3600,
          'EDT': -4*3600, 'CDT': -5*3600, 'MDT': -6*3600, 'PDT': -7*3600,
          'UTC': 0}
for z, off in tzones.items():
    tokmap[z] = ('ZONE', z, off)

repeats = ['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']
for r in repeats:
    tokmap[r]  = ('REPEAT', r)

keywords = [
    'IN', 'ON', 'AT', 'OF', 'THE', 'AND', 'BETWEEN', 'AFTER', 'BEFORE',
     'NEXT', 'EVERY', 'REPEAT', 'OTHER', 'TOMORROW', 'NOON', 'AM', 'PM'
]
for k in keywords:
    tokmap[k] = (k, k)


# -- set up the lexer

tokens = keywords + ['DIGIT', 'COLON', 'COMMA', 'ORDINAL',
    'MONTH', 'DOW', 'DOWS', 'UNIT', 'ZONE']
precedence = (
    ('left', 'AT'),
    ('left', 'COMMA', 'AND'),
)
def t_error(t):
    print(f"Unexpected character '%s' at %d" % (t.value[0],t.lexer.lexpos))

t_ignore = ' \t\n'
t_ORDINAL = '[2-9]*1st|[2-9*]*2nd|[2=9]*3rd|[1-9][0-9]*th'
t_DIGIT = r'[0-9]'
t_COLON = r':'
t_COMMA = r','

def t_token (t):
    '''[a-zA-Z.]+'''
    k = t.value.replace('.','').upper()
    try:
        v = tokmap[k]
    except KeyError:
        raise WhenError("I don't understand %s" % k)
    t.orig = t.value
    t.type = v[0]
    t.value = v[1]
    return t

# -- parser rules


def p_error(p):
    if p is None:
        raise WhenError('error at end of input')
    else:
        raise WhenError("error at %d  near %s" % (lexer.lexpos, p))

def p_whenevery_at(p):
    ''' when : every absdatetime'''
    rmap = {
        'day': 'bymonthday',
        'month': 'bymonth',
        'weekday': 'byweekday',
        'hour': 'byhour',
        'minute': 'byminute'
    }
    freq, kwargs = p[1]
    p[0] = []
    for kk in p[2]:
        kw = kwargs.copy()
        for k,v in kk.items():
            kw[rmap.get(k, k)] = v
        p[0].append((freq, kw))

def p_whenevery_bounded(p):
    '''when : every BETWEEN time AND time
            | every BETWEEN date AND date'''
    freq, kw = p[1]
    kw['dtstart'] = p[3]
    kw['until'] = p[5]
    p[0] = [ (freq, kw) ]

def p_whenevery(p):
    '''when : every'''
    p[0] = p[1]

def p_when(p):
    '''when : datetime'''
    p[0] = p[1]

def p_repeat(p):
    '''every : REPEAT'''
    unit = p[1]
    if unit == 'YEARLY': f=YEARLY
    if unit == 'MONTHLY': f=MONTHLY
    elif unit=='WEEKLY': f=WEEKLY
    elif unit=='DAILY': f=DAILY
    elif unit=='HOURLY': f=HOURLY
    p[0] = ( f, {} )

def p_every_unit(p):
    ''' every : EVERY UNIT
              | EVERY OTHER UNIT
              | EVERY amount UNIT
    '''
    if len(p) == 3:
        i = 2
        kwargs = {}
    else:
        i = 3
        if p[2] == 'OTHER':
            kwargs = { 'interval': 2 }
        else:
            kwargs = { 'interval': int(p[2]) }
    typ, unit = tokmap[p[i]]

    if unit == 'MONTH': f=MONTHLY
    elif unit == 'WEEK': f=WEEKLY
    elif unit == 'DAY': f=DAILY
    elif unit == 'HOUR': f=HOURLY
    p[0] = (f, kwargs)

def p_every_month(p):
    ''' every :  EVERY MONTH'''
    monum = tokmap[p[2]][2]
    p[0] = ( YEARLY, { 'bymonth': monum } )

def p_every_dow(p):
    ''' every : EVERY DOW
              | DOWS
    '''
    if p[1] == 'EVERY':
        idx = 2
    else:
        idx = 1
    danum = tokmap[p[idx]][2]
    p[0] = ( WEEKLY, { 'byweekday': danum } )


def p_datetime(p):
    '''datetime : absdatetime
                | ddelta absdatetime
                | absdatetime ddelta
                | ddelta
    '''
    if len(p) == 2:
        p[0] = p[1]
        return
    elif type(p[1]) is list:
        pl = p[1]
        r = p[2][0]
    elif type(p[2]) is list:
        pl = p[2]
        r = p[1][0]

    p[0] = []
    for pp in pl:
        pp.update(r)
        p[0].append(pp)

def p_ddelta(p):
    '''ddelta : in
              | next
    '''
    p[0] = p[1]

def p_in(p):
    ''' in : IN amount UNIT'''
    amt = p[2]
    unit = p[3]
    if not unit.endswith('s'): unit = unit+'s'
    p[0] = [ { unit.lower() : amt } ]

def p_next(p):
    ''' next : NEXT UNIT
             | NEXT MONTH
             | NEXT DOW
    '''
    val = p[2]
    tok = tokmap[val]

    if tok[0] == 'UNIT':
        if not val.endswith('s'): val+='s'
        p[0] =  { val.lower() : 1 }
    elif tok[0] == 'MONTH':
        monum = tokmap[val][2]
        p[0] = {'month': monum}
    elif tok[0] == 'DOW':
        val = val[:2].upper()
        p[0] = { 'weekday': tok[2] }
    else:
        p[0] = p[1]
    p[0] = [ p[0] ]


def p_absdatetime_simple(p):
    '''absdatetime : datelist
                   | timelist
    '''
    p[0] = p[1]

def p_absdatetime_multi(p):
    '''absdatetime : timelist datelist
                   | datelist timelist
    '''
    p[0] = []
    for pp in p[1]:
        for qq in p[2]:
            pq = {}
            pq.update(pp)
            pq.update(qq)
            p[0].append(pq)


def p_timelist_zone(p):
    '''timelist : timelist ZONE'''
    p[0] = p[1]
    offset = tzones.get(p[2])
    if offset is None:
        raise WhenError("I don't know a time zone named '%s'" % p[2])
    for pp in p[0]:
        pp['tzoffset'] = (p[2], offset)


def p_timelist(p):
    ''' timelist : timelist and time
                 | time
    '''
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [ p[1] ]

def p_datelist(p):
    ''' datelist : datelist and date
                 | date
    '''
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [ p[1] ]

def p_ondate(p):
    '''date : ON date'''
    p[0] = p[2]

def p_date(p):
    '''date : daymo'''
    p[0] = p[1]

def p_daymo_ord_indef(p):
    '''daymo : THE ORDINAL'''
    d = int(p[2][:-2])
    p[0] = { 'day' : d }

def p_daymo_ord(p):
    '''daymo : THE ORDINAL OF MONTH
             | MONTH ORDINAL
    '''
    danum = int(p[2][:-2])
    if len(p) == 5:
        monam = p[4]
    else:
        monam = p[1]
    monum = tokmap[monam][2]

    p[0] = { 'day': danum, 'month': monum }

def p_daymo(p):
    '''daymo : dom MONTH
            | DOW
            | TOMORROW
    '''
    if len(p) == 2:
        if p[1] == 'TOMORROW':
            p[0] = {'days': +1 }
        else:
            tok = tokmap[p[1]]
            p[0] = {'weekday': tok[2]}
    else:
        mo = tokmap[p[2]]
        p[0] = { "day": p[1],"month": mo[2] }


def p_dom(p):
    '''dom : DIGIT
           | DIGIT DIGIT
    '''
    p[0] = int(''.join(p[1:]))


def p_attime(p):
    '''time : AT time'''
    p[0] = p[2]

def p_time_noon(p):
    '''time : NOON'''
    p[0] = {'hour': 12, 'minute': 0}

def p_time(p):
    '''time : hrmin24
            | hrmin
            | hrmin_bare
    '''
    hm = p[1]
    if hm['hour'] > 23:
        raise WhenError("invalid hour: %d > 23" % hm['hour'])
    if hm['minute'] > 59:
        raise WhenError("invalid minute: %d > 59" % hm['minute'])
    p[0] = hm

def p_hrmin24(p):
    '''hrmin24 : hour minute'''
    p[0] = {'hour': p[1], 'minute': p[2]}

def p_hrmin_bare(p):
    '''hrmin_bare : hour COLON minute'''
    raise WhenError("must specify am or pm")

def p_hrmin(p):
    '''hrmin : hour COLON minute ampm
             | hour ampm
    '''
    if len(p) == 3:
        hm = {'hour': p[1], 'minute': 0}
        ampm = p[2]
    else:
        hm = {'hour': p[1], 'minute': p[3]}
        ampm = p[4]
    if ampm.lower() == 'pm':
        hm['hour'] += 12
    p[0] = hm

def p_ampm(p):
    '''ampm : AM
            | PM
    '''
    p[0] = p[1]

def p_hour(p):
    '''hour : DIGIT DIGIT
            | DIGIT
    '''
    hr = int(''.join(p[1:]))
    p[0] = hr

def p_minute(p):
    '''minute : DIGIT DIGIT '''
    min = int(''.join(p[1:]))
    p[0] = min

def p_comma_and(p):
    '''and : AND
           | COMMA
           | COMMA AND
    '''
    p[0] =  p[1]

def p_amount(p):
    '''amount : DIGIT
              | amount DIGIT
    '''
    if len(p) == 2:
        p[0] = int(p[1])
    else:
        p[0] = p[1]*10 + int(p[2])


lexer = lex.lex(errorlog=log)
parser = yacc.yacc(debug=DEBUG, errorlog=log)


## -- support functions


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

def getReqZone(req, default="UTC"):
    loc = None
    if req.user is not None:
        if req.user.tz:
            return (req.user.tz, None)

        loc = UserObj.lookup('here', requser=req.user)

    if not loc:
        try:
            ac = areaCodeFromPhone(req.frm)
            loc = Location.fromAreaCode(ac, req.user)
        except (LookupAreaCodeError, NotAnAreaCode) as e:
           loc = None

    if loc:
        zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
        return (zone, loc)

    return (default, None)


def getArgsZone(lnam, user):
    if lnam:
        loc = Location.fromInput(lnam, user)
        zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
        return zone, loc
    return None, None


def getReqNow(req):
    zone, _ = getReqZone(req)
    if zone:
        tzdata = ZoneInfo(zone)
    else:
        tzdata = timezone.utc
    return datetime.now(tzdata)


def mkdatetime(now, output_tz, kwargs):
    """ adjust datetime to UTC using desired offset (if given),
        zero-out second and microsecond
        and ensure it's in the future
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
    # passing in 'now' to ease testing
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
        zone, loc = getReqZone(req)
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
        zone, loc = getReqZone(req)
    now = datetime.now(tz=zone and ZoneInfo(zone))

    msg = "Current time is: %s" % now.ctime()
    msg+= "\nCurrent time zone is: %s" % zone
    if loc:
        msg+= "\n(Based on your %s of: %s)" % (loc.source, loc.orig)
    return msg


