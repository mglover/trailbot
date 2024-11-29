from datetime import datetime, timedelta
import os, stat, signal

from . import tb
from .core import TBError
from .cal import Calendar
from .user import User
from .dispatch import dispatch, TBRequest

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
            next = e.next(start)
            if not next:
                continue
            if next < stop:
                res.append((user, e.what))
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
        tz = timezone(timedelta(0))

        start = mkdatetime(datetime.now(), tz, {})
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