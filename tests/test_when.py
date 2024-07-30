import unittest
from datetime import datetime, timezone
from when import parser, mkdatetime, mkruleset, WhenError
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY,DAILY, HOURLY


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.expect = None
        self.expectError = None

    def tearDown(self):
        if self.expectError:
            self.assertRaises(self.expectError, parser.parse, self.input)
        else:
            res = parser.parse(self.input)
            self.assertEquals(self.expect, res)

class TestWhenAbsTimeNoWrap(ParserTest):

    def test_hrmin(self):
        self.input = "12:15am"
        self.expect = [ {'hour': 12, 'minute': 15} ]

    def test_pm_hour(self):
        self.input = "3pm"
        self.expect = [ {'hour': 15, 'minute': 0} ]

    def test_24hr(self):
        self.input = "1745"
        self.expect = [ {'hour': 17, 'minute': 45} ]

    def test_hour_minute_pm_dots(self):
        self.input = "7:37p.m"
        self.expect = [ {'hour': 19, 'minute': 37} ]

    def test_missing_ampm(self):
        self.input = "16:00"
        self.expectError = WhenError

    def test_time_list(self):
        self.input = "9am, noon, and 5:30pm"
        self.expect = [
            {'hour': 9, 'minute': 0},
            {'hour': 12, 'minute': 0},
            {'hour': 17, 'minute': 30}
        ]

class TestWhenRelTime(ParserTest):
    def test_in_hours(self):
        self.input = "in 3 hours"
        self.expect = [ {'hours': 3} ]

    def test_next_months(self):
        self.input = "next month"
        self.expect = [ {'months': 1} ]

class TestWhenAbsDate(ParserTest):
    def test_daymo(self):
        self.input = "19 July"
        self.expect = [ {'month': 7, 'day': 19} ]

    def test_on_daymo(self):
        self.input=("on September 11th")

    @unittest.skip("not detected here")
    def test_invalid_day(self):
        self.input = "32 Feb"
        self.expectError = WhenError

    def test_on_daymo(self):
        self.input = "on 1 August"
        self.expect = [ {'month': 8, 'day': 1} ]

    def test_ordinal(self):
        self.input = "the 18th"
        self.expect = [ {'day': 18} ]

    def test_onthe_ordinal(self):
        self.input = "the 3rd of September"
        self.expect = [ {'month': 9, 'day': 3} ]

    def test_ordinal_teen(self):
        self.input = "October  11th"
        self.expect = [ {'day': 11, 'month': 10} ]

    def test_ordinal_teen2(self):
        self.input = "the 12th"
        self.expect = [ {'day': 12} ]

    def test_daymo_list(self):
        self.input = "August 14th, the 13th of January, 3 October"
        self.expect = [
            {'month': 8, 'day': 14},
            {'month': 1, 'day': 13},
            {'month': 10, 'day': 3}
        ]

class TestWhenAbsDateTime(ParserTest):
    def test_daymo_time(self):
        self.input = "January 1st at noon"
        self.expect = [ {'day': 1, 'month': 1, 'hour': 12, 'minute': 0} ]

    def test_next_dow(self):
        self.input = "next wednesday"
        self.expect = [ {"weekday": 2} ]

    def test_dow_time(self):
        self.input = "thu at 6:45am"
        self.expect = [ {"weekday": 3, "hour":6, "minute": 45} ]

    def test_dow_24time(self):
        self.input = "fri at 0655"
        self.expect = [ {"weekday": 4, "hour": 6, "minute": 55} ]

    def test_ordinal_at(self):
        self.input = "on the 8th at 2pm"
        self.expect = [ {"day": 8, "hour": 14, "minute": 0} ]

    def test_zone(self):
        self.input = "May 10th at 9am CST"
        self.expect = [ {'day': 10, 'month': 5, 'hour': 9, 'minute': 0,
            'tzoffset': ('CST', -6*3600)} ]

class TestWhenRelDateTime(ParserTest):
    def test_ordinal_next(self):
        self.input = "the 11th next month"
        self.expect = [ {'day': 11, 'months': 1} ]

    def test_next_at24t(self):
        self.input = "next month at 1900"
        self.expect = [ {'months': 1, 'hour': 19, 'minute':0} ]

    def test_next_in_on(self):
        self.input = "in 3 months on the 3rd at 8:52pm"
        self.expect = [ { 'months': 3, 'day': 3, 'hour': 20, 'minute': 52} ]

    def test_tomrrow_at24(self):
        self.input = "tomorrow at 1700"
        self.expect =[ {'days': 1, 'hour': 17, 'minute': 0} ]

class TestWhenEvery(ParserTest):
    def test_daymo_time(self):
        self.input = "every month on the 9th at 3pm"
        self.expect = [ (MONTHLY, {
            'bymonthday': 9,
            'byhour': 15,
            'byminute': 0
        }) ]

    def test_dow_weekly(self):
        self.input = "weekly  on wednesday"
        self.expect = [ (WEEKLY, {'byweekday': 2}) ]

    def test_daily_time(self):
        self.input = "daily at 7:15pm"
        self.expect = [ (DAILY, {'byhour': 19, 'byminute': 15}) ]

    def test_eveydow_time(self):
        self.input = "every thursday at 10:30 a.m."
        self.expect = [ (WEEKLY, {
            'byweekday': 3,
            'byhour': 10,
            'byminute': 30
        }) ]

    def test_other_dow(self):
        self.input = "every other week on friday"
        self.expect = [ (WEEKLY, {'interval': 2, 'byweekday': 4}) ]

    def test_dows_time(self):
        self.input = "saturdays at noon"
        self.expect = [ (WEEKLY, {
            'byweekday': 5,
            'byhour': 12,
            'byminute': 0
        }) ]

    def test_hour_interval(self):
        self.input = "every 3 hours between 9am and 6 p.m."
        self.expect = [ (HOURLY, {
            'interval': 3,
            'dtstart': {'hour': 9, 'minute': 0},
            'until': {'hour': 18, 'minute': 0}
        }) ]

    def test_daily_multi(self):
        self.input = "every day at 9am, 11:30am, 2pm and 5pm"
        self.expect = [
            (DAILY, {'byhour': 9, 'byminute': 0}),
            (DAILY, {'byhour': 11, 'byminute': 30}),
            (DAILY, {'byhour': 14, 'byminute': 0}),
            (DAILY, {'byhour': 17, 'byminute': 0})
        ]

class DatetimeTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(1990, 6, 15, 13, 30, tzinfo=timezone.utc)
        self.tzinfo = timezone.utc

    def tearDown(self):
        e = self.expect.replace(tzinfo=timezone.utc)
        dt = mkdatetime(self.now, self.tzinfo, self.kwargs)
        self.assertEqual(e, dt)

class TestWhenWrap(DatetimeTest):
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

class TestWhenOffset(DatetimeTest):
    def test_hour(self):
        self.kwargs = {'hour': 14, 'minute': 0, 'tzoffset': ('EST', -5*3600)}
        self.expect = datetime(1990, 6, 15, 19, 0)

    def test_wrap_hour(self):
        self.kwargs = {'hour':8, 'minute': 0, 'tzoffset': ('EST', -5*3600)}
        self.expect = datetime(1990, 6, 16, 13, 0)

    def test_nowrap_equal(self):
        self.kwargs = {'hour':6, 'minute': 30, 'tzoffset': ('PDT', -7*3600)}
        self.expect = self.now



class TestMkRuleset(unittest.TestCase):
    def setUp(self):
        self.now = datetime(1990, 6, 15, 13, 30, tzinfo=timezone.utc)
        self.user = None # default, UTC timezone

    def getRules(self,input):
        return  mkruleset(self.now, input)

    def test_hrmin(self):
        rules = self.getRules("7pm")
        self.assertEqual(datetime(1990, 6, 15, 19, 0, tzinfo=timezone.utc),
             rules.after(self.now))

    def test_daymo(self):
        rules = self.getRules("19 July")
        self.assertEqual(datetime(1990, 7, 19, 13, 30, tzinfo=timezone.utc),
            rules.after(self.now))

