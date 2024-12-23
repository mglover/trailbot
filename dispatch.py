import logging, os, re, sys, traceback

from .core import TBError, success
from .shell_parser import parser, argsparser, lexer
from .response import TBResponse
from .user import User
from .userdata import UserObj
from .twilio import twiMLfromMessage, twiMLfromResponse

routes = []
cats = {}

log = logging.getLogger('dispatch')

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
    def __init__(self, user, frm, sms, argv=None):
        self.user = user
        self.frm = frm
        if argv:
            assert type(argv) is list
            # we were passed in pre-parsed args
            self.cmd = sms
            self.args = ' '.join(argv)
            self.argv = argv
            return

        self.argv = None
        p = sms.split(maxsplit=1)
        if len(p) == 2:
            self.cmd, self.args = p
        else:
            self.cmd = p
            self.args = ''

    @classmethod
    def fromPipeline(cls, ureq, pl):
        if pl.invar:
            args = Args.lookup(pl.invar, requser=ureq.user).args
        else:
            args = pl.args
        return cls(ureq.user, ureq.frm, pl.exe, argv=args)


    def __str__(self):
        return ', '.join((self.frm, self.cmd, self.args))


class TBUserRequest(object):
    def __init__(self, frm, cmd, user=None):
        if not frm or not cmd:
            raise EmptyRequest
        if user:
            assert user.phone == frm
            self.user = user
        else:
            self.user = User.lookup(frm, raiseOnFail=False, is_owner=True)
        self.frm = frm
        self.seq = parser.parse(cmd,lexer=lexer)


class Args(UserObj):
    typ = 'args'

    def __init__(self, args=None, **kwargs):
        super().__init__(**kwargs)
        self.args = args

    def toDict(self):
        return self.args

    def parseData(self, d):
        self.args = d

    @classmethod
    def fromString(cls, s, requser):
        return cls(
            argsparser.parse(s, lexer=lexer),
            requser=requser
        )
UserObj.register(Args)


def processPipeline(req, idx):
    pl = req.seq[idx]
    resp = ''
    while pl:
        if pl.invar:
            v = Args.lookup(pl.invar, requser=req.user)
            if not v:
                raise ValueError('not a var: %s' % pl.invar)
            pl.args = v.args
        elif resp:
            pl.args.append(resp)
        preq = TBRequest.fromPipeline(req, pl)
        act = getAction(pl.exe)
        resp = act(preq)
        if pl.outvar:
            Args.fromString(resp, requser=req.user).save(pl.outvar)
            resp = success("value saved")
        pl = pl.pipe

    return resp


def internal_dispatch(tbreq):
    msg = None
    try:
        for i in range(1):
            # XX how to merge multiple messages
            # XX which may not go to the same destination?
            msg = processPipeline(tbreq, i)

    except TBError as e:
        msg = str(e)

    except Exception as e:
        log.error(''.join(traceback.format_exc()))

    if msg is None:
        msg = "This is TrailBot:  something strange happened, "
        msg+= " I don't know how to respond. Try again?"

    if type(msg) == TBResponse:
        resp = msg
    else:
        resp = TBResponse()
        resp.addMsg(msg)

    if tbreq and tbreq.user:
        tbreq.user.setMore(resp.getMore())
        tbreq.user.release()

    return resp


def flask_dispatch(flask_req):
    frm = flask_req.args.get('From')
    sms = flask_req.args.get('Body')
    tbreq = TBUserRequest(frm, sms)
    resp = internal_dispatch(tbreq)
    return twiMLfromResponse(resp)