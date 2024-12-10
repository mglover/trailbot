from datetime import datetime, timedelta, timezone
import os, stat, signal, time

from .core import TBError
from .dispatch import internal_dispatch, TBUserRequest
from .user import User
from .when import UTC
from .cal import Calendar

class CronOverflow(TBError):
    msg = "CronBot failed to complete events in window: %s overflow"

class CronBot(object):
    def __init__(self):
        self.running = False

    def setSignals(self):
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def clearSignals(self):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def shutdown(self, *args):
        print("shutting down")
        self.running = False

    def perUser(self, user, start, stop):
        """ return a list of args for this user
            which are scheduled in this window
        """
        res = []
        if not user.cal: return res
        c = Calendar.fromUser(user)

        for e in c:
            if e.trigger.is_active(start, stop):
                res.append(e.action)
                e.trigger.fire(datetime.now(UTC))

        c.save()
        return res

    def perWindow(self, start, stop):
        res = []
        for u in User.list(is_owner=True):
            cmds = self.perUser(u, start, stop)
            for c in cmds:
                req = TBUserRequest(u.phone, c, user=u)
                res.append(internal_dispatch(req))
        return res


    def run(self):
        """ time-sycnronizing loop
            run forever, until signalled
            checking every minute-long window
            for user events
        """
        self.running = True

        start = datetime.now(UTC)
        stop = start + timedelta(minutes=1)

        while self.running:
            self.setSignals()
            print("Window", start, stop)
            res = self.perWindow(start, stop)

            for r in res:
                print("  r:", r.msgs)
                ## XX yes, do this
                """ send to phone"""

            start = stop
            stop = start + timedelta(minutes=1)
            now = datetime.now(UTC)

            slp = start-now
            print('slp', slp)
            self.clearSignals()
            if slp < timedelta(0):
                raise CronOverflow(slp)
            else:
                time.sleep(slp.total_seconds())


