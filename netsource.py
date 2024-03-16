import requests
from urllib.parse import urljoin

import config

class TBSession (requests.Session):
    def __init__(self):
        super().__init__()
        try:
            #raise AttributeError("No Proxies")
            self.proxies = {
                'http': config.PROXY,
                'https': config.PROXY
             }
        except AttributeError: 
            self.proxies = None
        self.verify = False
        self.headers = {
            "User-Agent": "TrailBot 1.4",
            "Referer": "http://oldskooltrailgoods.com/trailbot",
            "Connection": "keep-alive"
        }



proxy = TBSession()


class NetSource (object):
    name = None
    baseUrl = None

    def makeUrl(self, *arge, **kwargs):
        raise NotImplementedError

    def makeParams(self):
        raise NotImplementedError


    def __init__(self, *args, **kwargs):
        url =self.makeUrl(*args, **kwargs)
        params = self.makeParams(*args, **kwargs)
        self.err = None
        self.content = None

        try:
            with proxy.get(url, params=params) as resp:
                print("url '%s', params '%s'" %(url, params))
                if not resp.ok:
                    self.err = f"{self.name} failed to respond"
                self.content = resp.json()

        except requests.JSONDecodeError:
            self.err = f"Couldn't understand the response from {self.name}" + resp.text


