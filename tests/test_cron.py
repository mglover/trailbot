__package__ = 'trailbot'
import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .user import User
from .when import getUserZone
from .cal import Calendar, CalEntry
from .cron import CronBot
from tests.base import TBTest

class CronTest(unittest.TestCase):
    def setUp(self):
        self.bot = CronBot()
        self.uname = 't1'
        self.user = User.register('+0708666', self.uname)
        self.user.release()
        self.tzinfo = timezone(timedelta(0)) # UTC

    def tearDown(self):
        self.user.unregister()

    def getUser(self):
        self.user = User.lookup('@'+self.uname, is_owner=True)

    def releaseUser(self):
        self.user.release()
    def runRange(self, start, count=1, only_first=False):
        self.getUser()
        res = []
        for i in range(count):
            s = start+timedelta(minutes=i)
            e = s + timedelta(minutes=1)
            res += self.bot.perWindow(s, e)
        self.releaseUser()
        return res

    def injectEvents(self, *args):
        self.getUser()
        cal = Calendar.fromUser(self.user)
        a  = list(args)
        while len(a):
            when = a.pop(0)
            what = a.pop(0)
            cal.append(CalEntry(what, when, 'UTC'))
        cal.save()
        self.releaseUser()

    def test_simple(self):
        self.injectEvents('1830 UTC', 'echo hello')
        start = datetime(2024, 11, 28, 18, 30, tzinfo=self.tzinfo)
        evts = self.runRange(start)
        self.assertEqual(1, len(evts))
        self.assertEqual(self.user, evts[0][0])
        self.assertEqual('echo hello', evts[0][1])

