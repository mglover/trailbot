"""
in 3 hours
9am
1745
3pm
4p.m.
19 July
on 21 August
the 3rd of September
October 10th
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
every thursday at 10:30 a.m.
every 3 hours between 9am and 6 p.m.
every day at 9am, 11:30am, 2pm and 5pm
"""

from pkgs.ply import lex, yacc

from dateutil.relativedelta import relativedelta, weekdays
from dateutil.rrule import rrule, YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY
from datetime import date, datetime
import logging, time

from core import TBError


class WhenError(TBError):
    msg = "When? %s"


logging.basicConfig(
    level = logging.DEBUG,
    filename = "errors.txt",
    filemode = "w",
    format = "%(lineno)4d:%(message)s"
)
log = logging.getLogger()

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
    i += 1
tokmap['THUR'] = ('DOW', 'THURS', 4)

repeats = ['HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']
for r in repeats:
    tokmap[r]  = ('REPEAT', r)

keywords = [
    'IN', 'ON', 'AT', 'OF', 'THE', 'AND', 'BETWEEN', 'AFTER', 'BEFORE',
     'NEXT', 'EVERY', 'TOMORROW', 'AM', 'PM'
]
for k in keywords:
    tokmap[k] = (k, k)


# -- set up the leer

tokens = keywords + ['DIGIT', 'COLON', 'COMMA', 'ORDINAL',
    'MONTH', 'DOW', 'UNIT']

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
NOW = datetime.now()
TODAY = date.today()

def p_error(p):
    if p is None:
        print('error at end of input')
    else:
        print("error at %d  near %s" % (lexer.lexpos, p))

def p_whens(p):
    '''when : every
            | every absdatetime
            | every BETWEEN absdatetime AND absdatetime
    '''
    freq, fkwargs = p[1]
    if len(p) == 2:
        fkwargs['dtstart'] = NOW
    if len(p) == 3:
        fkwargs['dtstart'] = NOW + relativedelta(**p[2])
    else:
        fkwargs['dtstart'] = NOW + relativedelta(**p[3])
        fkwargs['until'] = NOW + relativedelta(**p[5])

    p[0] = rrule(freq, **fkwargs)

def p_when(p):
    '''when : datetime'''
    kwargs= p[1]

    kwargs['second'] = 0
    kwargs['microsecond'] = 0
    d = relativedelta(**kwargs)

    skip = 0
    while NOW + relativedelta(days=skip) + d < NOW:
        skip += 1
    p[0] = NOW + relativedelta(days=skip) + d


def p_every_unit(p):
    ''' every : EVERY UNIT
              | EVERY amount UNIT
    '''
    if len(p) == 3:
        i = 2
        amt = 1
    else:
        i = 3
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
    ''' every : EVERY DOW'''
    danum = tokmap[p[2]][2]
    p[0] = ( WEEKLY, { 'byweekday': danum } )


def p_datetime(p):
    '''datetime : absdatetime
                | ddelta absdatetime
                | absdatetime ddelta
                | ddelta
    '''
    p[0] = {}
    for pp in p[1:]:
        p[0].update(pp)

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
    p[0] = { unit.lower() : amt }

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
        if monum <= NOW.month:
            p[0]['years'] = +1
    elif tok[0] == 'DOW':
        val = val[:2].upper()
        p[0] = { 'weekday': tok[2]+1 }
    else:
        p[0] = p[1]


def p_dtlist(p):
    ''' dtlist :  dtcommas
               |  dtcommas AND absdatetime
    '''
    p[0] = p[1]
    if len(p) == 4:
        p[0].append(p[3])

def p_dtlist_comma(p):
    ''' dtcommas : dtlist COMMA absdatetime
                 | absdatetime
    '''
    if len(p) == 4:
        p[0] = p[1]
        p[0].append(p[3])
    else:
        p[0] = [ p[1] ]

def p_absdatetime(p):
    '''absdatetime : date
                   | time
                   | time date
                   | date time
    '''
    p[0] = {}
    for pp in p[1:]:
        p[0].update(pp)
    p[0]['second'] = 0
    p[0]['microsecond'] = 0

def p_ondate(p):
    '''date : ON date'''
    p[0] = p[2]

def p_date(p):
    '''date : daymo'''
    p[0] = p[1]

def p_daymo_ord_indef(p):
    '''daymo : THE ORDINAL'''
    p[0] = { 'day' : int(p[2][:-2]) }

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
            p[0] = {'day': tok[2]+1}
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

parser = yacc.yacc(debug=True, errorlog=log)


s = __doc__
for line in s.split('\n'):
    if not line or line.startswith('#'): continue
    try:
        res = parser.parse(line, debug=log)
    except TBError as e:
        res = str(e)
    print(line, "=>", res)
