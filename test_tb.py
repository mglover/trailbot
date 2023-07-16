#!/usr/bin/python
import unittest, os, sys
from base64 import b64encode
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from flask import Flask

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from trailbot.dispatch import TBResponse

from trailbot import tb


class TBTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.register_blueprint(tb.bp)

        self.cli = self.app.test_client()
        self.cred = b64encode(b"twilio:BananaPudding").decode('utf-8')

        self.frm1 = "+1888776666"
        self.frm2 = "+1999887777"

        self.req(self.frm1, "unreg")
        self.req(self.frm2, "unreg")

    def req(self, frm, args,
        do_auth=True, expect_status=200, only_first=True,
        **kw):
        if do_auth:
            if 'headers' not in kw:
                kw['headers'] = {}
            kw['headers']["Authorization"] = f"Basic {self.cred}"

        url = f"/fetch?"+urlencode({"From":frm, "Body":args})
        httpres = self.cli.get(url, **kw)
        self.assertEqual(httpres.status_code, expect_status)

        soup = BeautifulSoup(httpres.data, "xml")
        r = soup.find("Response")
        m = r.find_all("Message")

        if only_first:
            return m[0].contents[0]
        else:
            resp = TBResponse()
            for mm in m:
                resp.addMsg(mm.contents[0], to=mm.get('to'))
            return resp

    def req1(self, args, **kw):
        return self.req(self.frm1, args, **kw)
    def req2(self, args, **kw):
        return self.req(self.frm2, args, **kw)

    def reg1(self):
        self.assertSuccess(self.req1("reg @test1"))

    def reg2(self):
        self.assertSuccess(self.req2("reg @test2"))

    def assertStartsWith(self, res, start):
        if not res.startswith(start):
            raise AssertionError(f"'{res}' does not start with '{start}'")

    def assertSuccess(self, res):
        return self.assertStartsWith(res, "Success")

    def assertError(self, res):
        return self.assertStartsWith(res, "Err?")

    def test_help(self):
        res = self.req1("help")

    def test_help_wx(self):
        res = self.req1("help wx")
        self.assertStartsWith(res, 'wx -- get a 3 day weather report')

    def test_blurgl(self):
        res = self.req1("blurgl fop")
        self.assertStartsWith(res, "I don't know how")

    def test_reg(self):
        res = self.req1("whoami")
        self.assertEqual("You are not registered", res)

        res = self.req1('reg @test1')
        self.assertSuccess(res)

        res = self.req1('whoami')
        self.assertEqual("You are @test1", res)

    def test_unreg(self):
        self.reg1()
        res = self.req1("unreg")
        self.assertSuccess(res)

    def test_sub(self):
        self.reg1()
        self.assertStartsWith(self.req2("sub @test"), "I don't know any")
        res = self.req2("sub @test1")
        self.assertSuccess(res)

    def test_unsub(self):
        self.reg1()
        res = self.req2("unsub @test1")
        self.assertStartsWith(res, "You're not subscribed")
        self.assertStartsWith(self.req2("sub @test1"), "Success")

    def test_status(self):
        self.reg1()
        self.req1("status hello")
        self.assertEqual("@test1: hello", self.req2("status @test1"))

    def test_subs_status(self):
        self.reg1()
        self.reg2()
        self.assertSuccess(self.req2("sub @test1"))
        resp = self.req1("status foo", only_first=False)
        self.assertEqual(2, len(resp.msgs))
        self.assertSuccess(str(resp.msgs[1]))
        self.assertEqual(self.frm2, resp.msgs[0].kwargs['to'])
        self.assertEqual("@test1: foo", str(resp.msgs[0]))

    def test_status_subs(self):
        self.reg1()
        self.reg2()
        self.assertSuccess(self.req1("status foobar"))
        resp = self.req2("sub @test1", only_first=False)
        self.assertEqual(2, len(resp.msgs))
        self.assertSuccess(str(resp.msgs[0]))
        self.assertEqual("@test1: foobar", str(resp.msgs[1]))

    def test_status_empty(self):
        self.assertError(self.req1("status"))

    def test_status_none(self):
        self.reg1()
        res = self.req2("status @test1")
        self.assertEqual(res, "No status for test1")

    def test_dm(self):
        self.reg1()
        self.reg2()
        resp = self.req1("@test2 what's up", only_first=False)
        self.assertEqual(str(resp.msgs[0]), "@test1: what's up")
        self.assertEqual(self.frm2, resp.msgs[0].kwargs['to'])

    def test_where_nom(self):
        self.reg1()
        res = self.req1("where Empire State Building")
        self.assertStartsWith(res, "Empire State Building\n(full name")

    def test_where_citystate(self):
        res = self.req1("where portland, or")
        self.assertStartsWith(res, "portland, or")

    def test_where_zip(self):
        res = self.req1("where 97214")
        self.assertStartsWith(res, "97214")

    def test_here(self):
        self.reg1()
        res = self.req1("here portland, or")
        self.assertSuccess(res)

    def test_addr(self):
        self.reg1()
        self.assertSuccess(self.req1("addr buq Albuquerque, NM"))
        res = self.req1("where buq")
        self.assertStartsWith(res, "Albuquerque, NM")

    def test_here_nouser(self):
        res = self.req1("addr buq Albuquerque, NM")
        self.assertStartsWith(res, "You must register")

    def test_where_here(self):
        self.reg1()
        self.assertSuccess(self.req1("here portland, or"))
        res = self.req1("where here")
        self.assertStartsWith(res, "portland, or")

    def test_share_here(self):
        self.reg1()
        self.reg2()
        self.req1("here silver city, nm")
        self.assertSuccess(self.req1("share here with @test2"))
        resp = self.req2("where @test1.here")
        self.assertStartsWith(resp, "silver city, nm")

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

    def test_drive(self):
        res = self.req1("drive from seattle to portland, or")
        self.assertStartsWith(res, "Turn directions courtesy OSRM")

    def test_drive_here_there(self):
        self.reg1()
        self.assertSuccess(self.req1("here seattle"))
        self.assertSuccess(self.req1("there portland, or"))
        res = self.req1("drive")
        self.assertStartsWith(res, "Turn directions courtesy OSRM")

    def test_drive_no_here(self):
        self.assertError(self.req1("drive to seattle"))

    def test_drive_no_there(self):
        self.assertError(self.req1("drive from olympia, wa"))

    def test_forget(self):
        self.reg1()
        self.assertSuccess(self.req1("addr home New York City"))
        res = self.req1("where home")
        self.assertStartsWith(res, "New York City")
        self.assertSuccess(self.req1("forget home"))
        res = self.req1("where @test1")
        self.assertStartsWith(res, "Location not found:")

    def test_forget_nouser(self):
        res = self.req1("forget panama")
        self.assertStartsWith(res, 
            "You must register a @handle to use saved data")

if __name__ == '__main__':
    unittest.main()