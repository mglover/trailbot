import requests

from . import config
from .user import User, HandleUnknownError


baseurl_sending = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json" % config.TWILIO_ACCOUNT_SID


class Bot(object):
    handle = None
    phone = None

    def _isBotPhone(self, phone):
        assert type(phone) is str
        return self.phone.startswith("+07807")

    def __init__(self):
        assert self._isBotPhone(self.phone)
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone
        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)

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

