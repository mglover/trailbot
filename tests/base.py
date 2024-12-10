#!/usr/bin/python
import unittest
import os, sys
from base64 import b64encode
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from flask import Flask

from trailbot import tb, netsource
from trailbot import netsource
from trailbot.response import TBResponse
from trailbot.dispatch import routes

HAS_REMOTE = False

def remote_db(fxn):
    """skip tests that need remote resources
       if remote connections are unavailable"
    """
    if HAS_REMOTE:
        print('run', fxn)
        return fxn
    print('Skipping %s: no internet' % fxn.__name__)
    return unittest.skip("no internet")

class TBTest(unittest.TestCase):
    def setUp(self):
        if False: # XXX expect connection failures
            netsource.proxy = netsource.TestSessionConnectionError
        self.app = Flask(__name__)
        self.app.testing = True
        self.app.register_blueprint(tb.bp)

        self.cli = self.app.test_client()
        self.cred = b64encode(b"twilio:BananaPudding").decode('utf-8')

        self.frm1 = "+1888776666"
        self.frm2 = "+1999887777"

        self.req(self.frm1, "Unregister")
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
        self.assertSuccess(self.req1("Register @test1"))

    def reg2(self):
        self.assertSuccess(self.req2("reg @test2"))

    def assertStartsWith(self, res, start):
        if not res.startswith(start):
            raise AssertionError(f"'{res}' does not start with '{start}'")

    def assertNotStartsWith(self, res, start):
        if res.startswith(start):
            raise AssertionError(f"'{res}' starts with '{start}'")

    def assertSuccess(self, res):
        return self.assertStartsWith(res, "TrailBot: Success")

    def assertError(self, res):
        return self.assertStartsWith(res, "Err?")




class TestHelpLen(unittest.TestSuite):
    max_lengths = {}
    skips = ['help', 'whoami']

    def mkchecklen(self, mycmd, myfxn):
        class Testcls (unittest.TestCase):
            def runTest(s):
                try:
                    h = myfxn._help
                except AttributeError:
                    s.fail("No help for %s" % mycmd)
                    return False
                s.assertTrue(len(h) < self.max_lengths.get(mycmd, 160),
                    "help text for '%s' is too long (%d > 160)"
                    % (mycmd, len(h))
                )
        return Testcls()

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for cmd,fxn in routes:
            if cmd in self.skips: continue
            self.addTest(self.mkchecklen(cmd, fxn))

