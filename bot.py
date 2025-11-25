import os, time, sys, signal
from datetime import datetime, timedelta, timezone
from flask import render_template

from . import config, twilio
from .core import getPhoneClass
from .user import User, HandleUnknownError
from .group import Group, GroupUnknownError
from .when import mkruleset, mkdatetime


def log(msg):
   print(msg)
   sys.stdout.flush()


class BotError(Exception):
    msg = "%s"

class Bot(object):
    handle = None
    phone = None
    when = None

    _lockfd = None

    @property
    def lockfile(self):
        return os.path.join(self.user.dbpath, self.user.userdir, 'bot')

    def _obtainLock(self):
        while self._lockfd is None:
            mode = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_TRUNC
            try:
                fd = os.open(self.lockfile, mode)
            except FileExistsError:
                    log("Waiting on %s" % self.lockfile)
                    time.sleep(60)
            else:
                self._lockfd = fd

    def _releaseLock(self):
        if self._lockfd is not None:
            os.close(self._lockfd)
            self._lockfd = None
            try:
                os.remove(self.lockfile)
            except FileNotFoundError:
                log(f"{self.lockfile} did not exist anymore")

    def __init__(self):
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone
        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)
        self._obtainLock()
        log(f"{self.handle} next: {self.next()}")

    def next(self):
        now = mkdatetime(datetime.now(), timezone(timedelta(0)), {})
        rr = mkruleset(now, self.when)
        return next(rr.xafter(now, count=1))

    def run(self):
        raise NotImplementedError

    def shutdown(self):
        self._releaseLock()

    def getResponse(self, req):
        """Handle direct messages to this user"""
        return "Hmm. I don't know what to say to that."

    def send_to_phone(self, phone, msg):
        if phone == self.phone: return
        if getPhoneClass(phone) == 'bot'
            raise ValueError("Trying to send to bot phone %s" % phone)

        twilio.smsToPhone(phone, msg)


class ChannelBot(Bot):
    def __init__(self):
        assert getPhoneClass(self.phone) == 'bot')
        Bot.__init__(self)
        try:
            self.group = Group.fromTag(self.tag, self.user)
        except GroupUnknownError:
            self.group = Group.create(self.tag, self.user, 'announce')
        log("Ready.")


    def send_to_group(self, body):
        head = "From @%s in #%s" % (self.user.handle, self.group.tag)
        msg = '#%s: %s' % (head, body)
        msg = render_template(
            'chat.txt',
            user=self.user, group=self.group, msg=body
        )
        i=0
        for user in self.group.getReaders():
            self.send_to_phone(user.phone, msg)
            i+=1
        log('sent to %d users' % i)


class BotMon(object):
    def __init__(self, *botclasses):
        self.bots = [ bc() for bc in botclasses ]
        self.nexts = [ (b.next(), b) for b in self.bots ]
        self.nexts.sort()
        self.running = False

    def addEvent(self, dt, bot):
        self.nexts.append((dt, bot))
        self.nexts.sort()

    def getNext(self):
        dt, bot = self.nexts.pop(0)
        nxt = bot.next()
        if nxt:
            self.addEvent(nxt, bot)
        return dt, bot

    def update(self, signum, frame):
        print("updating")
        self.nexts = [bot.update() for bot in self.bots]
        self.nexts.sort()

    def shutdown(self, signum, frame):
        print("shutting down")
        self.running = False
        for bot in self.bots:
            bot.shutdown()
        raise BotError('reset')

    def run(self):
        self.running = True
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGINT, self.shutdown)
        while self.running:
            try:
                start = datetime.now(timezone(timedelta(0)))
                dt, bot  = self.getNext()
                slp = (dt  - start).total_seconds()
                if slp > 0:
                    time.sleep(slp)
                    bot.run()
            except BotError:
                pass
            except Exception as e:
                log(str(e))

