from tests.base import TBTest, remote_db

feedfile = "test_feed.xml"

feeds = (
    ("https://gmjournalist.substack.com/feed", ""),
    ("www.coffeeandcovid.com/feed", ""),
    ("coffeeandcovid.com", ""), #HTML w/ rel=alternate
    ("www.moonofalabama.org", ""), # Atom,
    ("https://cnbc.com", "Feed not found"),  # no RSS
    ("ecosophia.org", "")
)

class TestNews(TBTest):
    def test_empty(self):
        res = self.req1("news")
        self.assertStartsWith(res, "You must register")

    @remote_db
    def test_headlines(self):
        res = self.req1(f"news {feeds[0][0]}")
        self.assertStartsWith(res, f"{feeds[0][1]}")

    @remote_db
    def test_articles(self):
        for f in feeds:
            feed, starts = f
            res = self.req1(f"news {feed} 1")
            if starts:
                self.assertStartsWith(res, starts)
            else:
                self.assertNotStartsWith(res, "Feed not found")

    @remote_db
    def test_urlnoscheme(self):
        self.req1("notafeed")

    @remote_db
    def test_badfeed_badurl(self):
        res = self.req1("news {ab/cd")
        self.assertStartsWith(res, "Feed not found")

    @remote_db
    def test_saved(self):
        self.reg1()
        res = self.req1(f"news {feeds[0][0]} as is")
        self.assertSuccess(res)
        res = self.req1("news is")
        self.assertStartsWith(res, feeds[0][1])

    @remote_db
    def test_resave(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feeds[1][0]} as is"))
        self.assertSuccess(self.req1(f"news {feeds[0][0]} as is"))
        res = self.req1('news is')
        self.assertStartsWith(res, feeds[0][1])

    @remote_db
    def test_more(self):
        self.reg1()
        res = self.req1(f"news {feeds[0][0]} 1")
        self.assertNotStartsWith(res, "Feed not found")
        res = self.req1("more")
        self.assertNotStartsWith(res, "Nothing")

    @remote_db
    def test_more_nouser(self):
        res = self.req1(f"news {feeds[0][0]} 1")
        self.assertNotStartsWith(res, "Feed not found")
        res = self.req1("more")
        self.assertNotStartsWith(res, "Registration")