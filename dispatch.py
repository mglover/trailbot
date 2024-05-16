import re
from .core import TBError, TBMessage, TBResponse
from .user import User

routes = []

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

def tbroute(*specs):
    def fxn(cmd, *args, **kwargs):
        for spec in specs:
            routes.append((spec, cmd))
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
    def __init__(self, frm, cmd, args):
        self.frm = frm
        self.cmd = cmd
        self.args = args
        self.user = User.lookup(frm, raiseOnFail=False)

    def __str__(self):
        return ', '.join((self.frm, self.cmd, self.args))

    @classmethod
    def fromFlask(cls, request):
        frm = request.args.get('From')
        sms = request.args.get('Body')

        if not frm or not sms:
            raise EmptyRequest

        parts = sms.split(maxsplit=1)
        if len(parts)==2: cmd,args = parts
        else: cmd,args = sms,""
        cmd = cmd.lower()

        return cls(frm, cmd, args)



def dispatch(request):
    try:
        tbreq = TBRequest.fromFlask(request)
        act = getAction(tbreq.cmd)
        msg = act(tbreq)

    except TBError as e:
        msg = str(e)

    if msg is None:
        msg = "This is TrailBot:  something strange happened, "
        msg+= " I don't know how to respond. Try again?"

    if type(msg) == TBResponse:
        resp = msg
    else:
        resp = TBResponse()
        resp.addMsg(msg)

    return resp.asTwiML()
