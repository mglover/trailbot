import unittest
from base64 import b64encode
from bs4 import BeautifulSoup

import trailbot
from flask import Flask

class TBTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.register_blueprint(trailbot.bp)

        self.cli = self.app.test_client()
        self.cred = b64encode(b"twilio:BananaPudding").decode('utf-8')

        self.frm1 = "+1888776666"
        self.frm2 = "+1999887777"

        self.req(self.frm1, "unreg")
        self.req(self.frm2, "unreg")

    def req(self, frm, args, do_auth=True, **kw):
        if do_auth:
            if 'headers' not in kw:
                kw['headers'] = {}
            kw['headers']["Authorization"] = f"Basic {self.cred}"

        url = f"/fetch?From={frm}&Body={args}"

        httpres = self.cli.get(url, **kw)
        self.assertEqual(httpres.status_code, 200)

        soup = BeautifulSoup(httpres.data, "xml")
        res = soup.find("Message").contents[0]
        return res


    def test_help(self):
        res = self.req(self.frm1, "help")

    def test_reg(self):
        res = self.req(self.frm1, "whoami")
        self.assertEqual("You are not registered", res)
        res = self.req(self.frm1, 'reg @test1')
        self.assertTrue(res.startswith("Success: @test1 registered"), res)

        res = self.req(self.frm1, 'whoami')
        self.assertEqual("You are @test1", res)

if __name__ == '__main__':
    unittest.main()