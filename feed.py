__package__ = "trailbot"

import inscriptis, feedparser, dateutil.parser, re
from bs4 import BeautifulSoup as bs4
from urllib import parse
from datetime import datetime

from flask import render_template

from .core import parseArgs, TBError, success
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

    def __init__(self, url=None, last=None, orig_url=None, *args, **kwargs):
        self.url = url
        self.last = last
        self.orig_url = orig_url
        # XX make this work w super()?
        NetSource.__init__(self, *args, raiseOnError=True, **kwargs)
        UserObj.__init__(self, *args, **kwargs)

    def makeUrl(self, *args, **kwargs):
        self.name = self.url
        return self.url

    def toDict(self):
        d =  {'url': self.url}
        if self.orig_url:
            d['orig_url'] = self.orig_url
        if self.last:
            d['last'] = self.last.isoformat()
        return d

    def parseData(self, data):
        self.url = data['url']
        self.orig_url = data.get('orig_url')
        if data.get('last'):
            self.last = datetime.fromisoformat(data['last'])
        else:
            self.last = None

    @classmethod
    def fromInput(cls, str, requser):
        str = str.lower()
        if requser:
            # check saved data
            ud = cls.lookup(str, requser)
            if ud is not None: return ud
        return cls.fromInputUrl(str, requser)

    @classmethod
    def fromInputUrl(cls, orig_url, requser, scheme='https://'):
        urlreg = re.compile(r'[\w]+\.[\w]+')
        ps = [orig_url, scheme+orig_url]
        while ps:
            url = ps.pop(0)
            urlp = parse.urlparse(url)
            if not (urlp.scheme and urlreg.match(urlp.netloc)):
                continue
            try:
                obj = cls(url, orig_url=orig_url, requser=requser)
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
            if can:
                base =  can.get('href')
            else:
                base = resp.url
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
            if 'updated' in ent:
                pubdate = dateutil.parser.parse(ent.updated)
            else:
                pubdate = dateutil.parser.parse(ent.published)
            if (self.last is None) or (pubdate > self.last):
                new.append(ent)
            if newlast is None or pubdate > newlast:
                newlast = pubdate
        self.last = newlast
        if self.nam and self.requser:
            self.save()
        return new[:max]

    def toSMS(self, *args, **kwargs):
        try:
            return NetSource.toSMS(self, *args, **kwargs)
        except ResponseError:
            raise FeedNotFound('%s returned an error' % self.name)

    def makeFeedHeads(self, ents, links=False):
        if self.nam: src=self.nam
        elif self.orig_url: src = self.orig_url
        else: src = self.url

        def date(ent):
            if 'updated' in ent: return ent.updated
            return ent.published

        if not ents:
            return ''

        ret = "From %s:" % src
        for i,e in enumerate(ents):
            ret+='\n\t%d: ' % (i+1)
            ret+=e.title
            if links:
                ret+= " (%s)" % e.link
            ret+=" on %s" % date(e)
        return ret

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
    links = False
    args = dict(parseArgs(req.args, ['with', 'as']))
    if '' in args:
        a = args.get('','').split()
        url = a and a.pop(0)
        num = a and a.pop(0)
    else:
        url = None
        num = None

    if 'as' in args:
        # save feed with name
        if not url: raise NewsSyntaxError()
        feed = Feed.fromInput(url, req.user)
        if not req.user: raise RegistrationRequired("to save news")
        feed.save(nam=args['as'], requser=req.user)
        return success( "feed %ssaved as %s" % (feed.nam, args['as']) )

    if 'with' in args:
        if args['with'] == 'links':
            links=True
        else:
            raise NewsSyntaxError()

    if not url:
        # see new articles in all saved groups
        if not req.user:
            raise RegistrationRequired("to use saved news")
        feeds = Feed.search(req.user)
        if not feeds:
            return("You have no saved feeds")

        msg = []
        for f in feeds:
           try:
                ents = f.newer()
                if ents: msg.append(f.makeFeedHeads(ents, links))
           except (FeedNotFound,ResponseError) as e:
                msg.append("%s: %s" % (f.nam, str(e)))
        if len(msg):
            return '\n\n'.join(msg)
        else:
            return "Nothing new to report"

    if not num:
        # see new articles in this group
        feed = Feed.fromInput(url, req.user)
        ents = feed.newer()
        if ents:
            return feed.makeFeedHeads(ents, links)
        return "Nothing new from %s" % feed.url

    else:
        # read article N
        try:
            idx=int(num)-1
        except ValueError:
            raise NewsSyntaxError
        return feed.toSMS('detail', idx)

