from tests.base import TBTest

feedfile = "test_feed.xml"
feed1 = "https://gmjournalist.substack.com/feed"
feed2 = "www.coffeeandcovid.com/feed"
badfeed = "https://coffeeandcovid.com"

class TestNews(TBTest):
    def test_empty(self):
        res = self.req1("news")
        self.assertStartsWith(res, "Err?")

    def test_headlines(self):
        res = self.req1(f"news {feed1}")
        self.assertStartsWith(res, "From INSIDE SHIPPING on Substack")

    def test_article(self):
        res = self.req1(f"news {feed2} 1")
        self.assertNotStartsWith(res, "Feed not found")

    def test_article2(self):
        res = self.req1(f"news {feed2} 1")
        self.assertNotStartsWith(res, "Feed not found")

    def test_urlnoscheme(self):
        self.req1("feed2")

    def test_badfeed_noxml(self):
        res = self.req1(f"news {badfeed}")
        self.assertStartsWith(res, "Feed not found")

    def test_badfeed_badurl(self):
        res = self.req1("news {ab/cd")
        self.assertStartsWith(res, "Feed not found")

    def test_saved(self):
        self.reg1()
        res = self.req1(f"news {feed1} as is")
        self.assertSuccess(res)
        res = self.req1("news is")
        self.assertStartsWith(res, "From INSIDE SHIPPING on Substack")

    def test_resave(self):
        self.reg1()
        self.assertSuccess(self.req1(f"news {feed2} as is"))
        self.assertSuccess(self.req1(f"news {feed2} as is"))

    def test_more(self):
        self.reg1()
        res = self.req1(f"news {feed1} 1")
        self.assertNotStartsWith(res, "Feed not found")
        res = self.req1("more")
        self.assertNotStartsWith(res, "Nothing")