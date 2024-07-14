"""
in 3 hours
9am
10am EST
1745
3pm
4p.m.
19 July
on 21 August
the 3rd of September
October 10th
January 1st at noon
next month
next wednesday
the 11th next month
tomorrow at 1700
thu at 6:45am
fri at 0655
next month at 1900
16:00
on the 8th at 2pm
every month on the 9th at 3pm
monthly on the 12th at 1535 CDT
weekly  on wednesday
daily at 7:15pm
every thursday at 10:30 a.m.
every other week on friday
saturdays at  noon
every 3 hours between 9am and 6 p.m.
9am, 2pm, and 4pm EDT
every day at 9am, 11:30am, 2pm and 5pm
"""
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
from datetime import datetime

import logging, time

from .pkgs.ply import lex, yacc

from .config import DEBUG
from .core import TBError, success, parseArgs
from .dispatch import tbroute, tbhelp
from .user import needsreg
from .userdata import UserObj
from .location import Location

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

## time zone support functions

zf = TimezoneFinder()

def getUserZone(user):
    if user is None:
        return (None, None)
    if user.tz:
        return (user.tz, None)

    loc = UserObj.lookup('here', requser=user)
    if not loc:
        return (None, None)

    zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
    return (zone, loc.orig)

def getUserNow(user):
    zone, source = getUserZone(user)
    tzdata = zone and ZoneInfo(zone)
    return datetime.now(tzdata)

def mkDatetime(**kwargs):
    print(kwargs)
    now = datetime.now(kwargs.get('timezone'))
    if 'timezone' in kwargs: kwargs.pop('timezone')
    return now + relativedelta(**kwargs)

## setup the symbol table

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
          'EDT': -4*3600, 'CDT': -5*3600, 'MDT': -6*3600, 'PDT': -7*3600}
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


# -- set up the leer

tokens = keywords + ['DIGIT', 'COLON', 'COMMA', 'ORDINAL',
    'MONTH', 'DOW', 'DOWS', 'UNIT', 'ZONE']

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
    v = tokmap[k]
    t.orig = t.value
    t.type = v[0]
    t.value = v[1]
    return t

lexer = lex.lex(errorlog=log)


# ---

def p_error(p):
    if p is None:
        print('error at end of input')
    else:
        print("error at %d  near %s" % (lexer.lexpos, p))

def p_whenevery_at(p):
    ''' when : every absdatetime'''
    freq, fkwargs = p[1]
    p[0] = rruleset()
    for pp in p[2]:
        fk = fkwargs
        fk['dtstart'] = mkDatetime(**pp)
        p[0].rrule(rrule(freq, **fk))

def p_whenevery(p):
    '''when : every
            | every BETWEEN absdatetime AND absdatetime
    '''
    freq, fkwargs = p[1]
    if len(p) == 2:
        fkwargs['dtstart'] =  getUserNow(p.parser.user)
    else:
        if len(p[3]) != 1: raise WhenError("start time must be a single time")
        if len(p[5]) != 1: raise WhenError("end time must be a single time")
        fkwargs['dtstart'] = mkDatetime(**p[3][0])
        fkwargs['until'] = mkDatetime(**p[5][0])

    p[0] = rrule(freq, **fkwargs)

def p_when(p):
    '''when : datetime'''
    p[0] = []
    NOW = getUserNow(p.parser.user)
    for kwargs in p[1]:
        kwargs['second'] = 0
        kwargs['microsecond'] = 0
        if 'month' in kwargs and kwargs['month'] < NOW.month:
            kwargs['year'] = NOW.year + 1
        elif 'day' in kwargs and kwargs['day'] < NOW.day:
            kwargs['month'] = NOW.month + 1
        elif 'hour' in kwargs and kwargs['hour'] < NOW.hour:
            kwargs['day'] = NOW.day + 1
        elif 'minute' in kwargs and kwargs['minute'] < NOW.minute:
            kwargs['hour'] = NOW.hour + 1

        p[0].append( mkDatetime(**kwargs) )

def p_repeat(p):
    '''every : REPEAT'''
    unit = p[1]
    if unit == 'YEARLY': f=YEARLY
    if unit == 'MONTHLY': f=MONTHLY
    elif unit=='WEEKLY': f=WEEKLY
    elif unit=='DAILY': f=DAILY
    elif unit=='HOURLY': f=HOURLY
    p[0] = ( f, {'interval': 1} )

def p_every_unit(p):
    ''' every : EVERY UNIT
              | EVERY OTHER UNIT
              | EVERY amount UNIT
    '''
    if len(p) == 3:
        i = 2
        amt = 1
    else:
        i = 3
        if p[2] == 'OTHER':
            amt = 2
        else:
            amt = int(p[2])
    typ, unit = tokmap[p[i]]

    if unit == 'MONTH': f=MONTHLY
    elif unit == 'WEEK': f=WEEKLY
    elif unit == 'DAY': f=DAILY
    elif unit == 'HOUR': f=HOURLY
    p[0] = (f, {'interval': amt})

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
            pq['second'] = 0
            pq['microsecond'] = 0
            p[0].append(pq)


def p_timelist_zone(p):
    '''timelist : timelist ZONE'''
    p[0] = p[1]
    offset = tzones.get(p[2])
    if offset is None:
        raise WhenError("I don't know a time zone named '%s'" % p[2])
    for pp in p[0]:
        pp['timezone'] = tzoffset(p[2], offset)



def p_timelist(p):
    ''' timelist : ticommas
                 | ticommas AND time
                 | ticommas COMMA AND time
                 | time
    '''
    if type(p[1]) is list:
        p[0] = p[1]
    else:
        p[0] = [ p[1] ]
    if len(p) == 4:
        p[0].append(p[3])
    if len(p) == 5:
        p[0].append(p[4])

def p_tilist_comma(p):
    ''' ticommas : time COMMA time
                 | ticommas COMMA time
    '''
    if type(p[1]) is list:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [ p[1] , p[3] ]

def p_datelist(p):
    ''' datelist :  dacommas
                 |  dacommas AND date
                 |  dacommas COMMA AND date
    '''
    p[0] = p[1]
    if len(p) == 4:
        p[0].append(p[3])
    if len(p) == 5:
        p[0].append(p[4])

def p_dalist_comma(p):
    ''' dacommas : dacommas COMMA date
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

def p_amount(p):
    '''amount : DIGIT
              | amount DIGIT'''
    if len(p) == 2:
        p[0] = int(p[1])
    else:
        p[0] = p[1]*10 + int(p[2])

parser = yacc.yacc(debug=DEBUG, errorlog=log)


## TrailBot interface


@tbroute('tz', 'timezone')
@tbhelp('''tz -- set or get your time zone

say e.g.: 'tz America/New_York'
or: 'tz US/Eastern'
or just 'tz' to see the currently set zone

(if this isn't set, your current location (with 'here') will be used)
''')
@needsreg("to use time zones")
def tz(req):
    if not len(req.args.strip()):
        zone, source = getUserZone(req.user)
        if zone is None:
            return "No time zone or current location set"
        elif source is None:
            return "You have set your time zone to: %s" % zone
        else:
            msg = "Based on your current location of:\n  %s" % source
            msg+= "\n your time zone is\n  %s" % zone
            return msg
    try:
        req.user.tz = str(ZoneInfo(req.args))
    except (KeyError, ValueError):
        return "Not a valid time zone: %s" % req.args
    return success("Time zone set to %s" % req.user.tz)

@tbroute('untz', 'untimezone')
@tbhelp('''untz -- delete your time zone setting''')
@needsreg("to use time zones")
def untz(req):
    if not req.user.tz: return "No time zone set"
    req.user.tz = None
    return "Time zone deleted"

@tbroute('now')
@tbhelp('''now -- get current time in your timezone

see also: tz, here
''')
def now(req):
    args = dict(parseArgs(req.args, ['in']))
    lnam = args.get('in')
    if lnam:
        loc = Location.fromInput(lnam, requser=req.user)
        zone = zf.timezone_at(lng=float(loc.lon), lat=float(loc.lat))
        source = lnam
    else:
        zone, source = getUserZone(req.user)
    now = datetime.now(tz=ZoneInfo(zone))
    msg = "Current time is: %s" % now.ctime()
    msg+= "\nCurrent time zone is: %s" % zone
    if source:
        msg+= "\n(Based on your location of: %s)" % source
    return msg

@tbroute('when')
@tbhelp('''when -- parse a plain english date

say e.g: 'next tuesday'
or: 'every friday at 9am'
''')
def when(req):
    zone, source = getUserZone(req.user)
    tzinfo = zone and ZoneInfo(zone)
    print(tzinfo)
    NOW = getUserNow(req.user)
    if req.args.lower().lstrip().startswith('is '):
        req.args = req.args.lstrip()[3:]
    parser.user = req.user

    res = parser.parse(req.args)

    if type(res) in (rrule,rruleset):
        ct = 3
        res = res.xafter(NOW, count=ct)
    else:
        ct = len(res)
    print(NOW, res)
    evts = ',\n '.join([r.astimezone(tzinfo).ctime() for r in res])
    if ct > 1:
        msg = "%s is a recurring event. next %d recurrences:\n %s" \
            % (req.args, ct, evts)
    else:
        msg = '%s is %s' % (req.args, evts)
    return success(msg)

if __name__ == '__main__':
    s = __doc__
    for line in s.split('\n'):
        if not line or line.startswith('#'): continue
        try:
            print(line, "=>", end='')
            res = parser.parse(line)
        except TBError as e:
            res = str(e)
        print(res)
