import logging
from requests import request, Session, ConnectionError, JSONDecodeError
from urllib.parse import urljoin

from . import  config
from .core import TBError

class ConnectionError(TBError):
    msg = "%s failed to respond"
class ResponseError(TBError):
    msg = "%s returned an error"

log = logging.getLogger('netsource')

class TBSession (Session):
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
            raise ConnectionError("Mock Connection Failure")

proxy = TBSession()


class NetSource (object):
    name = None
    baseUrl = None
    method = "get"

    def makeUrl(self, *arge, **kwargs):
        raise NotImplementedError

    def makeParams(self, *args, **kwargs):
        return dict()

    def makeData(self, *args, **kwargs):
        return dict()

    def parse(self, resp, *args, **kwargs):
        try:
            return resp.json()
        except JSONDecodeError:
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

    @property
    def response(self):
        self._load()
        return self._response

    def __init__(self, *args, raiseOnError=False, **kwargs):
        self.err = None
        self._response = None
        self._content = None
        self.raiseOnError = raiseOnError
        self.args = args
        self.kwargs = kwargs

    def _load(self):
        if self._response and not self.err:
            return
        self.err = None
        self._response = None
        self._content = None

        url = self.makeUrl(*self.args, **self.kwargs)
        params = self.makeParams(*self.args, **self.kwargs)
        data = self.makeData(*self.args, **self.kwargs)

        try:
            self._response = proxy.request(
                method=self.method,
                url=url,
                params=params,
                data=data)
            if not self._response.ok:
                r = self._response
                log.info("%s returned error %s: %s" %
                    (url, r.status_code, r.content[:80])
                )
                if self.raiseOnError:
                    raise ResponseError(self.name)
                self.err = f"{self.name} returned an error"
            else:
                self._content = self.parse(self._response)

        except ConnectionError:
            if self.raiseOnError: raise ConnectionError(self.name)
            self.err = f"Couldn't connect to {self.name}"
