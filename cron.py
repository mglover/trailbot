from datetime import datetime, timedelta, timezone
import logging, os, stat, signal, time

from . import config
from .core import TBError
from .dispatch import internal_dispatch, TBUserRequest
from .user import User
from .when import UTC
from .cal import Calendar

log = logging.getLogger('cron')

def smsToLog(phone, msg):
    log.info("%s %s" % (phone, msg))


if config.DEBUG:
   sendMessage = smsToLog
else:
    import twilio
    sendMessage = twilio.smsToPhone


class CronError(TBError):
    pass

class CronLockingError(CronError):
    msg = "Status file exists: %s"


class CronBot(object):
    def __init__(self):
        self.running = False
        self.statusfile = "status"

    def setSignals(self, ts):
        if os.path.exists(self.statusfile):
            raise CronLockingError(self.statusfile)
        with open(self.statusfile,'x') as sfd:
                sfd.write("%s" % ts)

        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)

    def clearSignals(self):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.unlink(self.statusfile)

    def shutdown(self, *args):
        log.debug("shutting down")
        self.running = False

    def perUser(self, user, start, stop):
        """ return a list of args for this user
            which are scheduled in this window
        """
        cmds = []
        if not user.cal: return cmds
        c = Calendar.fromUser(user)

        for e in c:
            fired = False
            err = "no after: %s %s" % (e.trigger.when, e.trigger.created)
            if e.trigger.is_active(start, stop):
                cmds.append(e.action)
                e.trigger.fire(datetime.now(UTC))
                fired = True

            if not e.trigger.after(stop):
                e.trigger.complete()
                if not fired:
                    log.error(err)
                else:
                    log.debug(err)

        c.save()
        return cmds

    def perWindow(self, start, stop):
        rlist = []
        for u in User.list(is_owner=True):
            cmds = self.perUser(u, start, stop)
            for c in cmds:
                req = TBUserRequest(u.phone, c, user=u)
                rlist.append((u, internal_dispatch(req)))
            u.release()
        return rlist


    def run(self):
        """ time-sycnronizing loop
            run forever, until signalled
            checking every minute-long window
            for user events
        """
        self.running = True

        start = datetime.now(UTC)
        stop = start.replace(
            minute=start.minute+1,
            second=0,
            microsecond=0
        )

        while self.running:
            log.debug("Window ending: %s" % stop)
            self.setSignals(start.timestamp())

            for user, res in self.perWindow(start, stop):
                for msg in res.msgs:
                    dst= msg.kwargs.get('to', user.phone)
                    sendMessage(dst, msg.msg)

            start = stop
            stop = start + timedelta(minutes=1)
            now = datetime.now(UTC)

            slp = start-now
            log.debug('slp: %s' %slp)
            self.clearSignals()

            if slp < timedelta(0):
                log.error('overflow: %ss' % -slp)
            else:
                time.sleep(slp.total_seconds())


