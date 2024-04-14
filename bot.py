import os, requests, time

from . import config
from .user import User, HandleUnknownError


baseurl_sending = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % config.TWILIO_ACCOUNT_SID


class Bot(object):
    handle = None
    phone = None
    sleep = 30

    def _isBotPhone(self, phone):
        assert type(phone) is str
        return phone.startswith("+07807")

    def _obtainLock(self):
        gofile = os.path.join(self.user.dbpath, self.user.userdir, 'bot')
        done = False
        while not done:
            try:
                os.unlink(gofile)
                done = True
            except FileNotFoundError:
                print("Waiting on %s" % gofile)
                time.sleep(self.sleep)
                pass

    def _releaseLock(self):
        gofile = os.path.join(self.user.dbpath, self.user.userdir, 'bot')
        open(gofile, 'w').write('go')

    def __init__(self):
        assert self._isBotPhone(self.phone)
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone

        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)

        self._obtainLock()


    def __del__(self):
        self._releaseLock()


    def send_to_phone(self, phone, msg):
        if phone == self.phone: return
        if self._isBotPhone(phone):
            raise ValueError("Trying to send to bot phone %s" % phone)

        data = {
            'Body': msg,
            'MessagingServiceSid': config.TWILIO_MSG_SID,
            'To': phone
        }
        res = requests.post(
            baseurl_sending,
            data=data,
            auth=((config.TWILIO_API_USER, config.TWILIO_API_PASS))
        )
    # XXX check return code?

