import requests
from urllib.parse import urljoin

from . import  config
from .core import TBError

class ConnectionError(TBError):
    msg = "%s failed to respond"
class ResponseError(TBError):
    msg = "%s returned an error"

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

class TestSessionConnectionError(object):
    def __init__(self, *args, **kwargs):
        pass

    def get(self, *args, **kwargs):
            raise requests.ConnectionError("Mock Connection Failure")

proxy = TBSession()


class NetSource (object):
    name = None
    baseUrl = None

    def makeUrl(self, *arge, **kwargs):
        raise NotImplementedError

    def makeParams(self):
        raise NotImplementedError

    def makeContent(self, *arge, **kwargs):
        raise NotImplementedError

    def toSMS(self, *args, **kwargs):
        if self.err:
            return self.err
        else:
            return self.makeResponse(self.content, *args, **kwargs)

    def __init__(self, *args, raiseOnError=False, **kwargs):
        url =self.makeUrl(*args, **kwargs)
        params = self.makeParams(*args, **kwargs)
        self.err = None
        self.content = None

        try:
            with proxy.get(url, params=params) as resp:
                if not resp.ok:
                    if raiseOnError: raise ResponseError(self.name)
                    self.err = f"{self.name} returned an error"
                else:
                    self.content = resp.json()

        except requests.ConnectionError:
            if raiseOnError: raise ConnectionError(self.name)
            self.err = f"Couldn't connect to {self.name}"
        except requests.JSONDecodeError:
            self.err = f"Couldn't understand the response from {self.name}"
