from tests.base import TBTest

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
        self.assertStartsWith(res, "Err?")

    def test_headlines(self):
        res = self.req1(f"news {self.feeds[0][0]}")
        self.assertStartsWith(res, f"{self.feeds[0][1]}")

    def test_articles(self):
        for f in self.feeds:
            feed, starts = f
            res = self.req1(f"news {feed} 1")
            if starts:
                self.assertStartsWith(res, starts)
            else:
                self.assertNotStartsWith(res, "Feed not found")

    def test_urlnoscheme(self):
        self.req1("notafeed")

    def test_badfeed_badurl(self):
        res = self.req1("news {ab/cd")
        self.assertStartsWith(res, "Feed not found")

    def test_saved(self):
        self.reg1()
        res = self.req1(f"news {self.feeds[0][0]} as is")
        self.assertSuccess(res)
        res = self.req1("news is")
        self.assertStartsWith(res, self.feeds[0][1])

    def test_resave(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {self.feeds[1][0]} as is"))
        self.assertSuccess(self.req1(f"news {self.feeds[0][0]} as is"))
        res = self.req1('news is')
        self.assertStartsWith(res, self.feeds[0][1])

    def test_more(self):
        self.reg1()
        res = self.req1(f"news {self.feeds[0][0]} 1")
        self.assertNotStartsWith(res, "Feed not found")
        res = self.req1("more")
        self.assertNotStartsWith(res, "Nothing")
