import os, logging

from .user import User, HandleUnknownError
from .cal import Calendar, CalError
from .when import Zone, Event


class Bot(object):
    handle = None
    phone = None
    when = None
    what = None

    def __init__(self):
        try:
            self.user = User.lookup(self.handle, is_owner=True)
            assert self.phone == self.user.phone
        except HandleUnknownError:
            self.user = User.register(self.phone, self.handle)

        c = Calendar(self.user)
        try:
            c.append(self.what,
                Event(self.when, Zone.fromUser(self.user))
            )
        except CalError:
            pass

        c.save()
        self.user.release()

    def getResponse(self, req):
        """Handle direct messages to this user"""
        return "Hmm. I don't know what to say to that."


class WordBot(Bot):
    handle = '@WordBot'
    phone = '+078070001000'
    when = "daily at 1616"
    what = "twotd | #twodt"

