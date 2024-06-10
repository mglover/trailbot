from tests.base import TBTest

class TestMy(TBTest):
    def test_my_addrs(self):
        self.reg1()
        self.assertSuccess(self.req1("addr home New York City"))
        res = self.req1("my addrs")
        self.assertStartsWith(res, "You have 1 saved addrs")