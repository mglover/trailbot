from tests.base import TBTest

feedurl = "https://gmjournalist.substack.com/feed"
feedfile = "test_feed.xml"

class TestNews(TBTest):
    def test_empty(self):
        res = self.req1("news")
        self.assertStartsWith(res, "Err?")

    def test_headlines(self):
        res = self.req1(f"news {feedurl}")
        self.assertStartsWith(res, "From INSIDE SHIPPING on Substack")

    def test_article(self):
        res = self.req1(f"news {feedurl} 1")
        self.assertStartsWith(res, "In : The ")

    def test_urlnoscheme(self):
        self.req1("coffeeandcovid.com")

    def test_badfeed(self):
        res = self.req1(f"news {feedurl}xyz")
        self.assertStartsWith(res, "Feed not found")

    def test_saved(self):
        self.reg1()
        res = self.req1(f"news {feedurl} as is")
        self.assertSuccess(res)
        res = self.req1("news is")
        self.assertStartsWith(res, "From INSIDE SHIPPING on Substack")
