from tests.base import TBTest, remote_db
from tests.test_news import feeds

class TestMy(TBTest):
    @remote_db
    def test_my_addrs(self):
        self.reg1()
        self.assertSuccess(self.req1("addr home New York City"))
        res = self.req1("my addrs")
        self.assertStartsWith(res, "You have 1 saved addrs")

    @remote_db
    def test_my_news(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feeds[0][0]} as is" ))
        res = self.req1("my news")
        self.assertStartsWith(res, "You have 1 saved news")

    @remote_db
    def test_my_mix(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feeds[1][0]} as is" ))
        self.assertSuccess(self.req1("addr home New York City"))

        res = self.req1("my addrs")
        self.assertStartsWith(res, "You have 1 saved addrs")
        res = self.req1("my news")
        self.assertStartsWith(res, "You have 1 saved news")