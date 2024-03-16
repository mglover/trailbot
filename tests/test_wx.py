from tests.base import TBTest

class TestWx(TBTest):
    def test_wx(self):
        res = self.req1("wx seattle")
        self.assertStartsWith(res, "Downtown Seattle WA")

    def test_wx_there(self):
        self.reg1()
        self.assertSuccess(self.req1("there seattle"))
        res = self.req1("wx there")
        self.assertStartsWith(res, "Downtown Seattle WA")

    def test_wx_here(self):
        self.reg1()
        self.assertSuccess(self.req1("here denver, co"))
        res = self.req1("wx")
        self.assertStartsWith(res, "Denver CO")

    def test_wx_empty(self):
        res  = self.req1("wx")
        self.assertEqual("Weather report for where?", res)

