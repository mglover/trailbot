import unittest

from shell_parser import ShellError, ShellPipeline, parser, lexer

from tests.base import TBTest

class ShellTest(unittest.TestCase):
    def parse(self, msg):
        return parser.parse(msg, lexer=lexer)

    def test_simple(self):
        seq = self.parse("echo hello")
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEqual(pl.exe, 'echo')
        self.assertEqual(pl.args, ['hello'])
        self.assertEqual(pl.pipe, None)

    def test_pipeline(self):
        seq = self.parse("echo  hello | @test")
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEqual(pl.exe, 'echo')
        self.assertEqual(pl.args, ['hello'])
        self.assertEqual(pl.pipe.exe, '@test')

    def test_qstr(self):
        seq = self.parse('echo "hello world"')
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEqual(pl.exe, 'echo')
        self.assertEqual(pl.args, ['hello world'])

    def test_multiarg(self):
        seq = self.parse('echo hello world')
        self.assertEqual(1, len(seq))
        pl = seq[0]
        self.assertEqual(pl.exe, 'echo')
        self.assertEqual(pl.args, ['hello', 'world'])

    def test_sequence(self):
        seq = self.parse('echo hello;echo world')
        self.assertEqual(2, len(seq))
        self.assertEqual(['hello'], seq[0].args)
        self.assertEqual(['world'], seq[1].args)


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


class RedirectTest(TBTest):
    def test_redirect(self):
        self.reg1()
        res = self.req1("echo jukes > myword")
        self.assertSuccess(res)
        res = self.req1("echo < myword")
        self.assertEqual(res, 'jukes')


