from tests.base import TBTest

class TestHelp(TBTest):

    def test_help(self):
        res = self.req1("help")

    def test_help_wx(self):
        res = self.req1("help wx")
        self.assertStartsWith(res, 'wx -- get a 3 day weather report')

    def test_blurgl(self):
        res = self.req1("blurgl fop")
        self.assertStartsWith(res, "I don't know how")

    def test_ambiguous(self):
        res = self.req1("wh")
        self.assertStartsWith(res, "I know how to do several things")
