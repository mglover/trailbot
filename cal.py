import json, logging
from datetime import datetime, timedelta, timezone
from collections import UserList

try:
    from zoneinfo import ZoneInfo
except ModuleNotFoundError:
    from backports.zoneinfo import ZoneInfo

from .core import parseArgs, success, TBError
from .dispatch import tbroute, tbhelp
from .user import User, needsreg
from .when import Zone, Event

log = logging.getLogger("cal")

class CalError(TBError):
    msg="%s"


class CalEntry(object):
    def __init__(self, action, trigger):
        assert type(trigger) is Event, trigger
        self.action = action
        self.trigger = trigger

    def __eq__(self, other):
        assert type(other) is type(self), type(other)
        return self.action == other.action \
            and self.trigger == other.trigger

    def __repr__(self):
        return "%s do %s" % (self.trigger, self.action)

class Calendar(UserList):
    def __init__(self, user):
        super().__init__(self)
        self.user = user

    @classmethod
    def fromUser(cls, user):
        assert type(user) is User
        if user.cal is None:
            rows = []
        else:
            rows = json.loads(user.cal)

        self = cls(user)
        for d in rows:
            what = d['action']
            trig = Event.fromDict(d['trigger'])
            self.append(what, trig)
        return self

    def save(self):
        assert type(self.user) is User
        rows = []
        for e in self:
            trig = e.trigger.toDict()
            if trig:
                rows.append(
                    {'action': e.action, 'trigger': trig}
                )
        self.user.cal = json.dumps(rows)

    def append(self, what, trigger):
        e = CalEntry(what, trigger)
        if e in self: raise CalError("Event already exists")
        super().append(e)

    def remove(self, what, trigger):
        e = CalEntry(what, trigger)
        return super().remove(e)


@tbroute('cal', 'calendar', cat="cal")
@tbhelp('''cal -- schedule an event

e.g. to send yourself a weather report every morning at 9am, say:

   cal daily at 9pm do wx
''')
@needsreg("to use the calendar")
def cal(req):
    args = dict(parseArgs(req.args, ['do']))
    when = args['']
    what = args.get('do')
    now = datetime.now(timezone(timedelta(0)))

    c = Calendar.fromUser(req.user)

    if not what:
        ct = len(c)
        o = "%d events" % ct
        for i in range(ct):
            nxt = c[i]
            o+= "\t '%s': next  %s  do %s\n" % (
                c[i].trigger.when,
                c[i].trigger.after(now),
                c[i].action
            )
        return o

    zone  = Zone.fromUser(req.user)
    trig = Event(when, zone)
    c.append(what, trig)
    c.save()
    return success("calender entry saved")


@tbroute('uncal', 'uncalendar', cat="cal")
@tbhelp('''uncal -- unschedule an event
''')
@needsreg("to use the calendar")
def uncal(req):
    return "not yet"
