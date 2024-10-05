import json
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:
    from backports.zoneinfo import ZoneInfo

from .bot import UserBot
from .core import parseArgs, success, TBError
from .dispatch import tbroute, tbhelp
from .user import User, needsreg
from .when import mkruleset, getReqZone


class CalError(TBError):
    msg="%s"

class CalEntry(object):
    def __init__(self, what, when, zone):
        self.what = what
        self.when = when
        self.zone = zone
        now = datetime.now(ZoneInfo(self.zone))
        rrules = mkruleset(now, self.when)
        self.next = next(rrules.xafter(now, count=1))

    def __gt__(self, other):
        return self.next.__gt__(other.next)

    def __lt__(self, other):
        return self.next.__lt__(other.next)

    def __eq__(self, other):
        return (
            self.what == other.what
            and self.when == other.when
            and self.zone == other.zone
        )

class Calendar(object):
    def __init__(self, rows=None, user=None):
        if rows is None: rows=[]
        assert type(rows) is list
        assert type(user) is User
        self.user = user
        self.entries = []
        for what, when, zone in rows:
            self.add(what, when, zone)

    @classmethod
    def fromUser(cls, user):
        assert type(user) is User
        if user.cal is None:
            rows = []
        else:
            rows = json.loads(user.cal)
        return cls( rows, user=user )

    def save(self):
        assert type(self.user) is User
        self.user.cal = json.dumps([
            ( e.what, e.when, e.zone )
            for e in self.entries
        ])

    def add(self, what, when, zone):
        e = CalEntry(what, when, zone)
        if e in self.entries:
            raise CalError("Event already exists")
        self.entries.append(e)
        self.entries.sort()
        if self.entries[0] == e:
            """ new next. ping the cal server"""
            UserBot.update(self.user)
        return e



@tbroute('cal', 'calendar', cat="cal")
@tbhelp('''cal -- schedule an event
''')
@needsreg("to schedule events")
def cal(req):
    args = dict(parseArgs(req.args, ['do']))
    when = args['']
    what = args.get('do')
    if not what:
        raise CalError("Err? What do you want me to do?")
    c = Calendar.fromUser(req.user)
    zone, loc = getReqZone(req)
    c.add(what, when, zone)
    c.save()
    return success("calender entry saved")
