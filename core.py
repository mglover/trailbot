from requests import Session
from urllib.parse import urlencode

class TBError(Exception):
    msg = "TBError: '%s'"
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return self.msg % self.args


class TBSession (Session):
    def __init__(self):
        super().__init__()
        self.proxies = {
            'http': 'http://localhost:3182',
            'https': 'http://localhost:3182'
        }
        self.verify = False
        self.headers = {
            "User-Agent": "TrailBot 1.4",
            "Referer": "http://oldskooltrailgoods.com/trailbot",
            "Connection": "keep-alive"
        }

proxy = TBSession()