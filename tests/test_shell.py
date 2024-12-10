import unittest

from shell_parser import ShellError, ShellPipeline, parser, lexer

from tests.base import TBTest

class ShellTest(unittest.TestCase):
    def parse(self, msg):
        return parser.parse(msg, lexer=lexer)

    def test_simple(self):
        seq = self.parse("echo hello")
        self.assertEquals(1, len(seq))
        pl = seq[0]
        self.assertEquals(pl.exe, 'echo')
        self.assertEquals(pl.args, ['hello'])
        self.assertEquals(pl.pipe, None)

    def test_pipeline(self):
        seq = self.parse("echo  hello | @test")
        self.assertEquals(1, len(seq))
        pl = seq[0]
        self.assertEquals(pl.exe, 'echo')
        self.assertEquals(pl.args, ['hello'])
        self.assertEquals(pl.pipe.exe, '@test')

    def test_qstr(self):
        seq = self.parse('echo "hello world"')
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEquals(pl.exe, 'echo')
        self.assertEquals(pl.args, ['hello world'])

    def test_multiarg(self):
        seq = self.parse('echo hello world')
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEquals(pl.exe, 'echo')
        self.assertEquals(pl.args, ['hello', 'world'])

    def test_sequence(self):
        seq = self.parse('echo hello;echo world')
        self.assertEquals(2, len(seq))
        self.assertEquals(['hello'], seq[0].args)
        self.assertEquals(['world'], seq[1].args)


class PipelineTest(TBTest):
    def test_pipeline(self):
        self.reg1()
        self.reg2()
        res = self.req1("twl jukes | @test2")
        self.assertStartsWith(res, "@test1: YES")

    def test_pipeline_multi(self):
        self.reg1()
        self.reg2()
        res = self.req1("echo jukes | twl | @test2")
        self.assertStartsWith(res, "@test1: YES")
