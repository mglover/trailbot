__package__ = "trailbot"

import feedparser

from flask import render_template

from .core import TBError, success
from .dispatch import tbroute, tbhelp
from .netsource import NetSource
from .user import User, RegistrationRequired
from .userdata import UserObj

class NewsSyntaxError(TBError):
    msg = "Err? What kind of news do you want?"\
        + "Say 'help news' to learn more"

class FeedNotFound(TBError):
    msg = "Feed not found: %s"

class Feed (NetSource, UserObj):
    typ = 'url'

    def __init__(self, url=None, *args, **kwargs):
        self.url = url
        NetSource.__init__(self, *args, **kwargs)
        UserObj.__init__(self, *args, **kwargs)

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

        ud = cls.lookup(str.lower(), requser)
        if ud: return ud
        return cls(str, requser=requser)

    def parse(self, resp, *args, **kwargs):
        self.content = feedparser.parse(resp.content)

    def toLatestSMS(self):
        self._load()
        if self.err: raise FeedNotFound(self.url)
        return render_template("news_latest.txt", feed=self.content)

    def toDetailSMS(self, idx):
        self._load()
        if self.err: raise FeedNotFound(self.url)
        return render_template("news_detail.txt", feed=self.content, idx=idx)

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

    url = args.pop(0)
    feed = Feed.fromInput(url, req.user)

    if len(args) <1:
        return feed.toLatestSMS()

    scmd = args.pop(0)

    if  scmd == 'as':
        """save feed with name"""
        if not req.user:
            raise RegistrationRequired("to use saved news")
        nam = args.pop(0)
        feed.save(nam=nam, requser=req.user)
        return success(f"feed {feed.url} saved as {nam}")

    else:
        """read article N"""
        try:
            idx=int(scmd)-1
        except ValueError:
            raise NewsSyntaxError
        return feed.toDetailSMS(idx)
