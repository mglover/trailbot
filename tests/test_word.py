from tests.base import TBTest, remote_db

class TestWord(TBTest):
    @remote_db
    def testGoodWord(self):
        res = self.req1("word dog")
        self.assertStartsWith(res, "From Merriam-Webster's Collegiate Dictionary: dog: a carnivorous ")

    @remote_db
    def testBadWord(self):
        res = self.req1("word floofl")
        self.assertStartsWith(res, "No match for ")

    @remote_db
    def testBadWordNoClose(self):
        res = self.req1("word xxyxz")
        self.assertStartsWith(res, "No match for ")

class TestTWL(TBTest):
    def testYes(self):
        res = self.req1("twl dog")
        self.assertStartsWith(res, 'YES')

    def testNo(self):
        res = self.req1("twl asdf")
        self.assertStartsWith(res, "NO")

class TestFiveWord(TBTest):
    def testFW(self):
            self.reg1()
            res = self.req1("5word")
            self.assertStartsWith(res, "Try to guess")
            res = self.req1("5word flume")
            res = self.req1("5word quit")
            self.assertStartsWith(res, "You have quit")