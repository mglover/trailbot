import atexit, datetime, os, time, sys

from flask import render_template

from . import config, twilio
from .core import isBotPhone
from .user import User, HandleUnknownError
from .group import Group, GroupUnknownError


def log(msg):
   print(msg)
   sys.stdout.flush()


class Bot(object):
    handle = None
    phone = None
    runhr = None
    runmin = None

    _sleep = 60
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
                    time.sleep(self._sleep)
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

    @classmethod
    def trigger(cls):
        now = datetime.datetime.now()
        return now.hour== cls.runhr and now.minute==cls.runmin

    @classmethod
    def sleep(cls):
        time.sleep(cls._sleep)

    def __init__(self):
        assert isBotPhone(self.phone)
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone

        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)

        self._obtainLock()
        atexit.register(self._releaseLock)

    def __del__(self):
        self._releaseLock()


    def getResponse(self, req):
        """Handle direct messages to this user"""
        return "Hmm. I don't know what to say to that."

    def send_to_phone(self, phone, msg):
        if phone == self.phone: return
        if isBotPhone(phone):
            raise ValueError("Trying to send to bot phone %s" % phone)

        twilio.smsToPhone(phone, msg)



class ChannelBot(Bot):
    def __init__(self):
        Bot.__init__(self)
        log("%s at %d:%02d" % (self.handle, self.runhr, self.runmin))
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
        self.bots = [b() for b in botclasses]

    def run(self):
        while True:
            for b in self.bots:
                if b.trigger():
                    b.run()
                    b.sleep()
            Bot.sleep()

