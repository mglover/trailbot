#!/usr/bin/python
import unittest
from base64 import b64encode
from bs4 import BeautifulSoup

import trailbot
from flask import Flask


class TBTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.register_blueprint(trailbot.bp)

        self.cli = self.app.test_client()
        self.cred = b64encode(b"twilio:BananaPudding").decode('utf-8')

        self.frm1 = "+1888776666"
        self.frm2 = "+1999887777"

        self.req(self.frm1, "unreg")
        self.req(self.frm2, "unreg")

    def req(self, frm, args, do_auth=True, expect_status=200, **kw):
        if do_auth:
            if 'headers' not in kw:
                kw['headers'] = {}
            kw['headers']["Authorization"] = f"Basic {self.cred}"

        url = f"/fetch?From={frm}&Body={args}"

        httpres = self.cli.get(url, **kw)
        self.assertEqual(httpres.status_code, expect_status)

        soup = BeautifulSoup(httpres.data, "xml")
        res = soup.find("Message").contents[0]
        return res

    def req1(self, args):
        return self.req(self.frm1, args)
    def req2(self, args):
        return self.req(self.frm2, args)

    def reg1(self):
        return self.req1("reg @test1")

    def assertStartsWith(self, res, start):
        if not res.startswith(start):
            raise AssertionError(f"'{res}' does not start with '{start}'")

    def assertSuccess(self, res):
        return self.assertStartsWith(res, "Success")

    def test_help(self):
        res = self.req1("help")

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

    def test_where(self):
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

    def test_where_here(self):
        self.reg1()
        self.assertSuccess(self.req1("here portland, or"))
        res = self.req1("where here")
        self.assertStartsWith(res, "portland, or")

    def test_wx(self):
        res = self.req1("wx seattle")
        self.assertStartsWith(res, "Downtown Seattle WA")

    def test_wx_there(self):
        self.reg1()
        self.assertSuccess(self.req1("there seattle"))
        res = self.req1("wx there")
        self.assertStartsWith(res, "Downtown Seattle WA")

    def test_drive(self):
        res = self.req1("drive from seattle to portland, or")
        self.assertStartsWith(res, "Turn directions courtesy OSRM")

    def test_drive_here_there(self):
        self.reg1()
        self.assertSuccess(self.req1("here seattle"))
        self.assertSuccess(self.req1("there portland, or"))
        res = self.req1("drive")
        self.assertStartsWith(res, "Turn directions courtesy OSRM")

    def test_share_here(self):
        pass


if __name__ == '__main__':
    unittest.main()