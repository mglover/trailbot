import unittest
from datetime import datetime, timezone
from dateutil.rrule import \
    YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY

from when import Zone, Clock, Event

from tests.base import TBTest

class MkdatetimeTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(1990, 6, 15, 13, 30, tzinfo=timezone.utc)
        self.tzinfo = timezone.utc

    def tearDown(self):
        e = self.expect.replace(tzinfo=timezone.utc)
        clk = Clock(self.now)
        self.assertEqual(e, clk.add(**self.kwargs))

class TestWhenWrap(MkdatetimeTest):
    def test_wrap_minute(self):
        self.kwargs = {'hour': 13, 'minute': 15}
        self.expect = datetime(1990, 6, 16, 13, 15)

    def test_wrap_hour(self):
        self.kwargs = {'hour': 12, 'minute': 45}
        self.expect = datetime(1990, 6, 16, 12, 45)

    def test_wrap_day(self):
        self.kwargs = {'day': 10, 'hour': 13}
        self.expect = datetime(1990, 7, 10, 13, 30)

    def test_wrap_daymonth(self):
        self.kwargs = {'day': 10, 'month': 6}
        self.expect = datetime(1991, 6, 10, 13, 30)

    def test_wrap_month(self):
        self.kwargs = {'month': 4}
        self.expect = datetime(1991, 4, 15, 13, 30)

    def test_nowrap_daymonth(self):
        self.kwargs = {'month': 6, 'day': 15 }
        self.expect = datetime(1990, 6, 15, 13, 30)


class TestWhenOffset(MkdatetimeTest):
    def test_hour(self):
        self.kwargs = {'hour': 14, 'minute': 0, 'tzoffset': ('EST', -5*3600)}
        self.expect = datetime(1990, 6, 15, 19, 0)

    def test_wrap_hour(self):
        self.kwargs = {'hour':8, 'minute': 0, 'tzoffset': ('EST', -5*3600)}
        self.expect = datetime(1990, 6, 16, 13, 0)

    def test_nowrap_equal(self):
        self.kwargs = {'hour':6, 'minute': 30, 'tzoffset': ('PDT', -7*3600)}
        self.expect = self.now


class TestWhenRelative(MkdatetimeTest):
    def test_in(self):
        self.kwargs = {'weekday': 4}
        self.expect = datetime(1990, 6, 15, 13, 30)


class TestEvent(unittest.TestCase):
    def setUp(self):
        self.now = datetime(1990, 6, 15, 13, 30, tzinfo=timezone.utc)

    def getRules(self,input):
        e = Event(input, self.now.tzinfo, created=self.now)
        e._mkRules()
        return e._rules

    def test_hrmin(self):
        rules = self.getRules("7pm")
        self.assertEqual(
            datetime(1990, 6, 15, 19, 0, tzinfo=timezone.utc),
             rules.after(self.now)
        )

    def test_daymo(self):
        rules = self.getRules("19 July")
        self.assertEqual(
            datetime(1990, 7, 19, 13, 30, tzinfo=timezone.utc),
            rules.after(self.now)
        )

    def test_bounds(self):
        rules= self.getRules("every hour between 9pm and 1am")
        evts = [ e for e in rules.xafter(self.now, count=7) ]
        self.assertEqual(
            datetime(1990, 6, 15, 21, 0, tzinfo=timezone.utc),
            evts[0]
        )
        self.assertEqual(
            datetime(1990, 6, 16, 1, 0, tzinfo=timezone.utc),
            evts[-1]
        )


class TestWhenAction(TBTest):
    def test_when_relative(self):
        resp = self.req1("when next monday")
        self.assertStartsWith(resp, "next monday is:")
