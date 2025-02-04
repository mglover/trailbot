import os, logging

from .user import User, HandleUnknownError
from .cal import Calendar
from .when import Zone, Event


class Bot(object):
    handle = None
    phone = None
    when = None
    what = None

    def __init__(self):
        try:
            self.user = User.lookup(self.handle)
            assert self.phone == self.user.phone
        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)

        try:
            c = Calendar.fromUser(self.user)
            c.append(self.what, Event(self.when
        except CalError:
            pass

    def getResponse(self, req):
        """Handle direct messages to this user"""
        return "Hmm. I don't know what to say to that."


class WordBot(Bot):
    handle = '@WordBot'
    phone = '+078070001000'
    when = "daily at 1616"
    what = "twotd | #twodt"

