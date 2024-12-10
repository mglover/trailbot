from tests.base import TBTest, remote_db

class TestDM(TBTest):
    def test_dm(self):
        self.reg1()
        self.reg2()
        resp = self.req1("@test2 what's up", only_first=False)
        self.assertEqual(resp.msgs[0].msg, "@test1: what's up")
        self.assertEqual(self.frm2, resp.msgs[0].kwargs['to'])


class TestReg(TBTest):
    def test_reg(self):
        res = self.req1("whoami")
        self.assertEqual("You are not registered", res)

        res = self.req1('register @test1')
        self.assertSuccess(res)

        res = self.req1('whoami')
        self.assertEqual("You are @test1", res)

    def test_unreg(self):
        self.reg1()
        res = self.req1("unreg")
        self.assertSuccess(res)

class TestAddr(TBTest):
    def test_here(self):
        self.reg1()
        res = self.req1("here portland, or")
        self.assertSuccess(res)

    def test_rehere(self):
        self.reg1()
        self.assertSuccess(self.req1("here deming,nm"))
        self.assertSuccess(self.req1("here lordsburg, nm"))
        res = self.req1("where here")
        self.assertStartsWith(res, '"lordsburg')

    def test_addr(self):
        self.reg1()
        self.assertSuccess(self.req1("addr buq Albuquerque, NM"))
        res = self.req1("where buq")
        self.assertStartsWith(res, '"Albuquerque, NM')

    def test_here_nouser(self):
        res = self.req1("addr buq Albuquerque, NM")
        self.assertStartsWith(res, "You must register")

    def test_where_here(self):
        self.reg1()
        self.assertSuccess(self.req1("here portland, or"))
        res = self.req1("where here")
        self.assertStartsWith(res, '"portland, or')

    def test_share_here(self):
        self.reg1()
        self.reg2()
        self.req1("here silver city, nm")
        self.assertSuccess(self.req1("share here with @test2"))
        resp = self.req2("where @test1.here")
        self.assertStartsWith(resp, '"silver city, nm')

    @remote_db
    def test_forget(self):
        self.reg1()
        self.assertSuccess(self.req1("addr home New York City"))
        res = self.req1("where home")
        self.assertStartsWith(res, '"City of New York')
        self.assertSuccess(self.req1("forget home"))
        res = self.req1("where @test1")
        self.assertStartsWith(res, "Location not found:")

    @remote_db
    def test_forget_nouser(self):
        res = self.req1("forget panama")
        self.assertStartsWith(res, 
            "You must register a @handle to use saved data")

    def testNoWord(self):
        res = self.req1("word")
        self.assertStartsWith(res, "Which word")
