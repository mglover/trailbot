__package__ = "trailbot"

import inscriptis, feedparser, dateutil, re
from bs4 import BeautifulSoup as bs4
from urllib import parse
from datetime import datetime

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

class HTMLHasAlternate(TBError):
    pass

class Feed (NetSource, UserObj):
    typ = 'url'

    def __init__(self, url=None, last=None, *args, **kwargs):
        self.url = url
        self.last = last
        # XX make this work w super()?
        NetSource.__init__(self, *args, raiseOnError=True, **kwargs)
        UserObj.__init__(self, *args, **kwargs)

    def makeUrl(self, *args, **kwargs):
        self.name = self.url
        return self.url

    def toDict(self):
        d =  {'url': self.url}
        if self.last:
            d['last'] = self.last.isoformat()
        return d

    def parseData(self, data):
        self.url = data['url']
        if data.get('last'):
            self.last = datetime.fromisoformat(data['last'])
        else:
            self.last = None

    @classmethod
    def fromInput(cls, str, requser):
        str = str.lower()
        # saved data
        ud = cls.lookup(str, requser)
        if ud: return ud
        else: return cls.fromInputUrl(str, requser)
        url = cls.findFeedUrl(str)
        return cls(str, requser=requser)

    @classmethod
    def fromInputUrl(cls, url, requser, scheme='https://'):
        urlreg = re.compile(r'[\w]+\.[\w]+')
        ps = [url, scheme+url]
        while ps:
            url = ps.pop(0)
            urlp = parse.urlparse(url)
            if not (urlp.scheme and urlreg.match(urlp.netloc)):
                continue
            try:
                obj = cls(url, requser=requser)
                if obj.content:
                    return obj
            except FeedNotFound:
                continue
            except HTMLHasAlternate as href:
                newurl = href.args[0]
                ps.append(newurl)

        raise FeedNotFound("Invalid URL: %s" % url)


    def parse(self, resp, *args, **kwargs):
        c = feedparser.parse(resp.content)
        if c.bozo:
            # not rss, maybe it's html w/ link rel=alternate
            html = bs4(resp.content, features="lxml")
            can = html.find('link', rel="canonical")
            if can: base =  can.get('href')
            else: base = None

            feed_urls = html.findAll("link", rel="alternate")
            for f in feed_urls:
                t = f.get('type')
                if t and ('rss' in t or 'xml' in t):
                    href = f.get("href")
                    if href:
                        if base and not parse.urlparse(href).scheme:
                            href= base+href
                        raise HTMLHasAlternate(href)

            raise FeedNotFound(c.bozo_exception)
        return c

    def newer(self, max=5):
        new = []
        if 'published' in self.content.feed:
            newlast = dateutil.parser.parse(self.content.feed.published)
        else : newlast=None

        for ent in self.content.entries:
            pubdate = dateutil.parser.parse(ent.published)
            if self.last is None or pubdate > self.last :
                new.append(ent)
            if newlast is None or pubdate > newlast:
                newlast = pubdate
        self.last = newlast
        self.save()
        return new[:max]

    def toSMS(self, *args, **kwargs):
        try:
            return NetSource.toSMS(self, *args, **kwargs)
        except ResponseError:
            raise FeedNotFound('%s returned an error' % self.name)

    def makeResponse(self, scmd, *args, **kwargs):
        feed = self.content
        if self.err: raise FeedNotFound(self.url)
        if scmd == 'latest':
            return render_template("news_latest.txt", feed=feed)
        else:
            idx = int(args[0])
            ent = feed.entries[idx]
            citems = ent.get('content')
            sitems = ent.get('summary')
            if citems:
                content = inscriptis.get_text(citems[0]['value'])
            elif sitems:
                content = inscriptis.get_text(sitems)
            return render_template("news_detail.txt", feed=feed,
                ent = ent, content=content)

UserObj.register(Feed)


@tbroute('news')
@tbhelp('''news -- fetch and follow RSS feeds
  you can say
    'news FEED' to see the latest headlines from FEED
    'news FEED N' to read the N'th most recent article from FEED
    'news FEED as NAME' to save FEED with the shortcut NAME
  or just:
    'news'
  to get headlines from your saved feeds

where FEED is the URL for an RSS or Atom feed, or (for
registered users) the NAME of a saved feed

''')
def news(req):
    if req.args: args = req.args.split(' ')
    else: args=[]

    if len(args) <1:
        if not req.user:
            raise RegistrationRequired("to use saved news")
        feeds = Feed.search(req.user)
        if not feeds:
            return("You have no saved feeds")
        new = {}

        for f in feeds:
            n = f.newer()
            if n: new[f.nam] = n
        return render_template('news.txt', new=new)

    url = args.pop(0)
    feed = Feed.fromInput(url, req.user)

    if len(args) <1:
        return feed.toSMS('latest')

    scmd = args.pop(0)
    if scmd == 'as':
        """save feed with name"""
        if not req.user: raise RegistrationRequired("to save news")
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
