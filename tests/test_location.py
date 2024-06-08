from tests.base import TBTest

class TestWhere(TBTest):
    def test_where_nom(self):
        self.reg1()
        res = self.req1("where Empire State Building")
        self.assertStartsWith(res, "Empire State Building")

    def test_where_citystate(self):
        res = self.req1("where portland, or")
        self.assertStartsWith(res, "portland, or")

    def test_where_zip(self):
        res = self.req1("where 97214")
        self.assertStartsWith(res, "97214")

