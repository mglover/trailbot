import re, os, traceback

from .core import TBError
from .shell_parser import parser, lexer
from .twilio import TBResponse
from .user import User

routes = []
cats = {}

class EmptyRequest(TBError):
    msg = "No request"

class UnknownAction(TBError):
    msg ="I don't know how to do %s. \n"
    msg+="msg 'help me' for a list of commands, "
    msg+="or visit oldskooltrailgoods.com/trailbot "
    msg+="to view the full documentation."


class AmbiguousAction(TBError):
    msg = "I know how to do several things that start with '%s'."
    msg+= "\nDid you mean one of these?"
    msg+= "\n\n%s"


def tbhelp(helpmsg):
    def fxn(cmd, *args, **kwargs):
        cmd._help = helpmsg
        return cmd
    return fxn

def tbroute(*specs, cat=None):
    def fxn(cmd, *args, **kwargs):
        for spec in specs:
            routes.append((spec, cmd))
        if cat:
            if cat not in cats: cats[cat] = []
            cats[cat].append((specs, cmd))
        return cmd
    return fxn

def matchesSpec(search, spec):
    assert type(search) in (str, re.Pattern)
    return \
        type(spec) == re.Pattern \
            and spec.match(search) \
        or type(spec) == str \
            and spec.startswith(search) \

def getAction(search_cmd):
    m = [(spec,cmd) for spec, cmd in routes
        if matchesSpec(search_cmd, spec)]
    if len(m) == 0: raise UnknownAction(search_cmd)
    if len(m) > 1:
        for s,c in m:
            if s == search_cmd: return c
        raise AmbiguousAction(search_cmd, '\n'.join([i[0] for i in m]))
    return m[0][1]


class TBRequest(object):
    def __init__(self, frm, cmd):
        seq = parser.parse(cmd,lexer=lexer)
        self.frm = frm
        self.cmd = seq[0].exe
        if seq[0].args:
            self.args = ' '.join(seq[0].args)
        else:
            self.args = ''
        self.user = User.lookup(frm, raiseOnFail=False, is_owner=True)

    def __str__(self):
        return ', '.join((self.frm, self.cmd, self.args))

    @classmethod
    def fromFlask(cls, request):
        frm = request.args.get('From')
        sms = request.args.get('Body')

        if not frm or not sms:
            raise EmptyRequest

        return cls(frm, sms)


def dispatch(request):
    tbreq = None
    msg = None
    try:
        tbreq = TBRequest.fromFlask(request)
        act = getAction(tbreq.cmd)
        msg = act(tbreq)

    except TBError as e:
        msg = str(e)

    except Exception as e:
        traceback.print_exc()

    if msg is None:
        msg = "This is TrailBot:  something strange happened, "
        msg+= " I don't know how to respond. Try again?"

    if type(msg) == TBResponse:
        resp = msg
    else:
        resp = TBResponse()
        resp.addMsg(msg)

    r = resp.asTwiML()
    if tbreq and tbreq.user:
        tbreq.user.setMore(resp.getMore())
        tbreq.user.release()

    return r
