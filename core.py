from requests import Session
from urllib.parse import urlencode

from . import config


class TBError(Exception):
    msg = "TBError: '%s'"
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return self.msg % self.args


def parseArgs(args, keywords):
    """ search the request for values separated by keywords 
        return a dict of keyword, value pairs.
    """

    # find the first occasion of each keyword, create a sorted
    # (offset, keyword) list
    args = ' '+args
    keywords = [ ' '+k.strip()+' ' for k in keywords ]
    keylocs = [
        (args.find(k), k)
        for k in keywords
        if args.find(k)>=0]
    keylocs.sort()

    if not len(keylocs):
        return [('', args.strip())]

    first_loc = keylocs[0][0]

    values = []
    if first_loc > 0:
        # there's text before the first keyword
        values.append(( '', args[0:first_loc].strip() ))

    for i in range(len(keylocs)):
        # list is (offset, keyword
        start, kw = keylocs[i]
        start += len(kw)

        # get the end of the substring
        if i <= len(keylocs)-2:
            end = keylocs[i+1][0]
        else:
            end = len(args)

        values.append((kw.strip(), args[start:end]))
    return values


class TBSession (Session):
    def __init__(self):
        super().__init__()
        try:
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