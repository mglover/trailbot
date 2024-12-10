from tests.base import TBTest


class TestSub(TBTest):
    def test_sub(self):
        self.reg1()
        res = self.req2("sub @test3")
        self.assertStartsWith(res, "I don't know any")
        res = self.req2("subscribe @test1")
        self.assertSuccess(res)

    def test_unsub(self):
        self.reg1()
        res = self.req2("unsub @test1")
        self.assertStartsWith(res, "You're not subscribed")
        self.assertSuccess(self.req2("sub @test1"))

class TestStatus(TBTest):
    def test_status(self):
        self.reg1()
        self.req1("status hello")
        self.assertEqual("TrailBot: status for @test1: hello", 
            self.req2("status @test1"))

    def test_subs_status(self):
        self.reg1()
        self.reg2()
        self.assertSuccess(self.req2("sub @test1"))
        resp = self.req1("status foo", only_first=False)
        self.assertEqual(2, len(resp.msgs))
        self.assertSuccess(str(resp.msgs[1]))
        self.assertEqual(self.frm2, resp.msgs[0].kwargs['to'])
        self.assertEqual("TrailBot: update from @test1: foo", 
            resp.msgs[0].msg)

    def test_status_subs(self):
        self.reg1()
        self.reg2()
        self.assertSuccess(self.req1("status foobar"))
        resp = self.req2("sub @test1", only_first=False)
        self.assertEqual(2, len(resp.msgs))
        self.assertSuccess(str(resp.msgs[0]))
        self.assertEqual("@test1: foobar", str(resp.msgs[1].msg))

    def test_status_empty(self):
        self.assertError(self.req1("status"))

    def test_status_none(self):
        self.reg1()
        res = self.req2("status @test1")
        self.assertEqual(res, "No status for test1")

