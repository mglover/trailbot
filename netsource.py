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

    def makeParams(self, *args, **kwargs):
        return dict()

    def parse(self, resp, *args, **kwargs):
        try:
            return resp.json()
        except requests.JSONDecodeError:
            self.err = f"Couldn't understand the response from {self.name}"
            return None

    def makeResponse(self, *arge, **kwargs):
        return self.content

    def toSMS(self, *args, **kwargs):
        if self.err:
            return self.err
        else:
            try:
                return self.makeResponse(*args, **kwargs)
            except TypeError:
                return  f"Got a bad repsonse from {self.name}"

    @property
    def content(self):
        self._load()
        return self._content

    def __init__(self, *args, raiseOnError=False, **kwargs):
        self.err = None
        self._content = None
        self.raiseOnError = raiseOnError
        self.args = args
        self.kwargs = kwargs

    def _load(self):
        self.err = None
        self._content = None
        url = self.makeUrl(*self.args, **self.kwargs)
        params = self.makeParams(*self.args, **self.kwargs)
        try:
            with proxy.get(url, params=params) as resp:
                if not resp.ok:
                    if self.raiseOnError:
                        raise ResponseError(self.name)
                    self.err = f"{self.name} returned an error"
                else:
                    self._content = self.parse(resp)

        except requests.ConnectionError:
            if self.raiseOnError: raise ConnectionError(self.name)
            self.err = f"Couldn't connect to {self.name}"
