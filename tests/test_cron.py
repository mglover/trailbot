__package__ = 'trailbot'
import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from .user import User
from .when import Zone, Clock, Event
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

    def runRange(self, count=1, only_first=False, **kwargs):
        clk = Clock(datetime.now(), tzinfo=self.tzinfo)
        start = clk.add(**kwargs)
        res = []
        for i in range(count):
            s = start+timedelta(minutes=i)
            e = s + timedelta(minutes=1)
            res += self.bot.perWindow(s, e)
        return res

    def injectEvents(self, *args):
        self.getUser()
        cal = Calendar.fromUser(self.user)
        a  = list(args)
        while len(a):
            when = a.pop(0)
            what = a.pop(0)
            cal.append(what, Event(when, Zone.fromName('UTC')))
        cal.save()
        self.releaseUser()

    def test_simple(self):
        self.injectEvents('1830 UTC', 'echo hello')
        evts = self.runRange(hour=18, minute=29, count=2)

        self.assertEqual(1, len(evts))
        self.assertEqual(self.user, evts[0][0])
        self.assertEqual('echo hello', evts[0][1])

    def test_two(self):
        self.injectEvents(
            '1830 UTC', 'echo greenwich',
            '1130 MST', 'echo hello gila'
        )
        evts = self.runRange(hour=18, minute=30)
        self.assertEqual(2, len(evts))

    def test_remove(self):
        self.injectEvents(
            '1830 UTC', 'echo oneshot'
        )
        self.runRange(hour=18, minute=30)
        evts = self.runRange(hour=18, minute=30)
        self.assertEqual(0, len(evts))

    def test_empty(self):
        evts = self.runRange(hour=18, minute=30)