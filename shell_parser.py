__package__ = 'trailbot'

import logging

from .pkgs.ply import lex, yacc

from .config import DEBUG
from .core import TBError


if DEBUG:
    log = logging.getLogger('shell_parser')
else:
    log = None


class ShellError(TBError):
    pass
class EOFError(ShellError):
    msg = 'error at end of input'
class SyntaxError(ShellError):
    msg = "error at %d near %s"


class ShellPipeline(object):
    def __init__(self, exe, args=None, pipe=None, redir=None):
        self.exe = exe
        self.args = args or []
        self.pipe = pipe
        self.redir = redir

tokens = ( 'PIPE', 'SEM', 'GT', 'LT', 'STR', 'QSTR' )
t_PIPE = r'\|'
t_SEM = r';'
t_GT = r'>'
t_LT = r'<'
t_QSTR = r'\"[^"]*\"'
t_STR = r'[^ |;<>"\t\n]+'

t_ignore = ' \t\n'

def p_error(p):
    if p is None:
        raise EOFError()
    else:
        raise SyntaxError(lexer.lexpos, p)


def p_sequence(p):
    """sequence : sequence  SEM  pipeline
    """
    p[0] = p[1]
    p[0].append(p[3])

def p_sequence_single(p):
    """sequence : pipeline
    """
    p[0] = [ p[1] ]

def p_pipeline(p):
    """ pipeline : command PIPE pipeline
    """
    p[0] = p[1]
    p[0].pipe = p[3]

def p_pipeline_simple(p):
    """ pipeline : command
    """
    p[0] = p[1]

def p_command_args(p):
    """ command : exe args
    """
    p[0] = ShellPipeline(p[1], p[2])

def p_command(p):
    """ command : exe
    """
    p[0] = ShellPipeline(p[1])

def p_args(p):
    """  args : args arg
    """
    p[0] = p[1] + [ p[2] ]

def p_args_simple(p):
    """ args : arg
    """
    p[0] = [ p[1] ]

def p_arg(p):
    """ arg : STR
            | qstr
    """
    p[0] = p[1]

def p_exe(p):
    """ exe : STR
    """
    p[0] = p[1].lower()

def p_qstr(p):
    """ qstr : QSTR
    """
    p[0] = p[1][1:-1]


lexer = lex.lex(errorlog=log)
parser = yacc.yacc(debug=DEBUG, errorlog=log)

__all__ = ('lexer', 'parser')