from tests.base import TBTest
from tests.test_news import feed1, feed2

class TestMy(TBTest):
    def test_my_addrs(self):
        self.reg1()
        self.assertSuccess(self.req1("addr home New York City"))
        res = self.req1("my addrs")
        self.assertStartsWith(res, "You have 1 saved addrs")

    def test_my_news(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feed1} as is" ))
        res = self.req1("my news")
        self.assertStartsWith(res, "You have 1 saved news")

    def test_my_mix(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feed1} as is" ))
        self.assertSuccess(self.req1("addr home New York City"))

        res = self.req1("my addrs")
        self.assertStartsWith(res, "You have 1 saved addrs")
        res = self.req1("my news")
        self.assertStartsWith(res, "You have 1 saved news")