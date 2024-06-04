__package__ = "trailbot"

import feedparser

from flask import render_template

from .core import TBError
from .dispatch import tbroute, tbhelp
from .netsource import NetSource
from .user import User, RegistrationRequired
from .userdata import UserObj

class NewsSyntaxError(TBError):
    msg = "Err? What kind of news do you want?"\
        + "Say 'help news' to learn more"


class Feed (NetSource, UserObj):
    typ = 'url'

    def __init__(self, url, *args, **kwargs):
        self.url = url
        super().__init__(self, *args, **kwargs)


    def makeUrl(self, *args, **kwargs):
        self.name = self.url
        return self.url

    def toDict(self):
        return {'url': self.url}

    def parseData(self, data):
        self.url = data['url']

    @classmethod
    def fromInput(cls, str, requser):
        parts = str.split()
        if len(parts) >1:
            raise NewsSyntaxError

        ud = cls(str.lower(), requser)
        if ud: return ud

        return cls(str, requser=requser)

    def parse(self, resp, *args, **kwargs):
        self.content = feedparser.parse(resp.content)

UserObj.register(Feed)



@tbroute('news')
@tbhelp('''news -- fetch and follow RSS feeds
  you can say 
    'news FEED' to see the latest headlines from FEED
    'news FEED N' to read the N'th most recent article from FEED
    'news FEED as NAME' to save FEED with the shortcut NAME

where FEED is the URL for an RSS or Atom feed, or (for
registered users) the NAME of a saved feed

XX link to docs here XX
''')
def news(req):
    if not req.args:
        raise NewsSyntaxError
    args = req.args.split(' ')
    if len(args) <1:
        raise NewsSyntaxError

    feed = Feed.fromInput(args.pop(0), req.user)

    if len(args) <1:
        return render_template("news_latest.txt", feed=feed.content)

    scmd = args.pop(0)

    if  scmd == 'as':
        """save feed with name"""
        if not req.user:
            raise RegistrationRequired("to use saved news")
        nam = args.pop(0)
        feed.save(nam=nam, requser=req.user)

    else:
        """read article N"""
        try:
            idx=int(scmd)-1
        except ValueError:
            raise NewsSyntaxError
        return render_template("news_detail.txt", feed=feed.content, idx=idx)
