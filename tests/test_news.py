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