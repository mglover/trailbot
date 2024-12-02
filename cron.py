from datetime import datetime, timedelta
import os, stat, signal

from . import tb
from .core import TBError
from .dispatch import dispatch, TBRequest
from .user import User
from .when import Clock
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
        signal.signal(signal.SIGTERM, None)
        signal.signal(signal.SIGINT, None)

    def shutdown(self):
        self.running = False

    def perUser(self, user, start, stop):
        """ return a list of (User, args) tuples
            which are scheduled in this window
        """
        res = []
        if not user.cal: return res
        c = Calendar.fromUser(user)

        for e in c:
            if e.trigger.is_active(start, stop):
                res.append((user, e.action))
                e.trigger.fire(datetime.now())

        c.save()
        return res

    def perWindow(self, start, stop):
        res = []
        for u in User.list(is_owner=True):
            res += self.perUser(u, start, stop)
            u.release()
        return res

    def processEvents(self, evts):
        for user, cmd in evts:
            req = TBRequest(user.phone, cmd)
            resp = dispatch(req)
            print(resp)
            #twilio.smsToPhone(user.phone, resp)

    def run(self):
        """ time-sycnronizing loop
            run forever, until signalled
            checking every minute-long window
              for user events
        """
        self.setSignals()
        self.running = True

        # XX ???  we must set *a* timezone
        # XX ??? but is this always/ever correct?
        utc = timezone(timedelta(0))

        start = Clock(datetime.now(), tzinfo=utc).dt
        stop = start + timedelta(minutes=1)

        while self.running:
            evts = self.perWindow(start, stop)
            self.processEvents(evts)

            start = stop
            stop = start + timedelta(minutes=1)
            now = datetime.now(tzinfo=tz)

            slp = start-now
            if slp < 0:
                raise CronOverflow(slp)
            else:
                time.sleep(slp)

        self.clearSignals()


@tb.bp.cli.command('cron')
def cron():
    CronBot().run()