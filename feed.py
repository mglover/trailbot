__package__ = "trailbot"

import feedparser
from urllib import parse

from flask import render_template

from .core import TBError, success
from .dispatch import tbroute, tbhelp
from .netsource import NetSource, ResponseError
from .user import User, RegistrationRequired
from .userdata import UserObj

class NewsSyntaxError(TBError):
    msg = "Err? What kind of news do you want?"\
        + "Say 'help news' to learn more"

class FeedNotFound(TBError):
    msg = "Feed not found: %s"

class Feed (NetSource, UserObj):
    typ = 'url'

    @classmethod
    def setUrl(self, url):
        self.url = None
        prxs =  ['', 'https://', 'http://']
        try:
            while not self.url:
                prx = prxs.pop(0)
                urlp = parse.urlparse(prx+url)
                if urlp.scheme and urlp.netloc:
                    self.url = url
                return
        except IndexError:
            raise FeedNotFound("Not a valid URL")

    def __init__(self, url=None, *args, **kwargs):
        if url: self.setUrl(url)
        # XX make this work w super()?
        NetSource.__init__(self, *args, raiseOnError=True, **kwargs)
        UserObj.__init__(self, *args, **kwargs)

    def makeUrl(self, *args, **kwargs):
        self.name = self.url
        return self.url

    def toDict(self):
        return {'url': self.url}

    def parseData(self, data):
        self.setUrl(data['url'])

    @classmethod
    def fromInput(cls, str, requser):
        str = str.lower()
        # saved data
        ud = cls.lookup(str, requser)
        if ud: return ud
        return cls(str, requser=requser)

    def parse(self, resp, *args, **kwargs):
        self._content = feedparser.parse(resp.content)

    def toSMS(self, *args, **kwargs):
        try:
            return NetSource.toSMS(self, *args, **kwargs)
        except ResponseError:
            raise FeedNotFound('%s returned an error' % self.name)

    def makeResponse(self, scmd, *args, **kwargs):
        if self.err: raise FeedNotFound(self.url)
        if scmd == 'latest':
            return render_template("news_latest.txt", feed=self.content)
        else:
            return render_template("news_detail.txt", feed=self.content,
                idx=args[0])

UserObj.register(Feed)



@tbroute('news')
@tbhelp('''news -- fetch and follow RSS feeds
  you can say
    'news FEED' to see the latest headlines from FEED
    'news FEED N' to read the N'th most recent article from FEED
    'news FEED as NAME' to save FEED with the shortcut NAME
where FEED is the URL for an RSS or Atom feed, or (for
registered users) the NAME of a saved feed

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
        return feed.toSMS('latest')

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
        return feed.toSMS('detail', idx)
