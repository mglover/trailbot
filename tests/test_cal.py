from tests.base import TBTest

class TestCal(TBTest):
    def test_noreg(self):
        res = self.req1("cal 9am do echo hello world")
        self.assertStartsWith(res, "You must register")

class TestUserCal(TBTest):
    def setUp(self):
        TBTest.setUp(self)
        self.reg1()

    def test_add(self):
        res = self.req1("cal 9am do echo hello")
        self.assertSuccess(res)

    def test_add_twice(self):
        cmd = "cal 9am do news"
        self.req1(cmd)
        res = self.req1(cmd)
        self.assertStartsWith(res, "Event already")

    def test_list(self):
        self.req1("cal 9am do echo hello")
        res = self.req1("cal")