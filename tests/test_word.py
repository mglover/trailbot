from tests.base import TBTest

class TestWord(TBTest):
    def testGoodWord(self):
        res = self.req1("word dog")
        self.assertStartsWith(res, "From Merriam-Webster's Collegiate Dictionary: dog: a carnivorous ")

    def testBadWord(self):
        res = self.req1("word floofl")
        self.assertStartsWith(res, "No match for ")

    def testBadWordNoClose(self):
        res = self.req1("word xxyxz")
        self.assertStartsWith(res, "No match for ")

