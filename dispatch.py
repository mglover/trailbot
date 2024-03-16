import re
from trailbot.user import User
from trailbot.core import TBError

routes = []

class EmptyRequest(TBError):
    msg = "No request"

class UnknownAction(TBError):
    msg ="I don't know how to do %s. \n"
    msg+="msg 'help' for a list of commands, "
    msg+="or visit oldskooltrailgoods.com/trailbot "
    msg+="to view the full documentation."


class AmbiguousAction(TBError):
    msg = "I know how to do several things that start with '%s'."
    msg+= "\nDid you mean one of these?"
    msg+= "\n\n%s"


class TBRequest(object):
    def __init__(self, frm, cmd, args):
        self.frm = frm
        self.cmd = cmd
        self.args = args
        self.user = User.lookup(frm, raiseOnFail=False)

    def __str__(self):
        return ', '.join((self.frm, self.cmd, self.args))

    @classmethod
    def fromFlask(cls,request):
        frm = request.args.get('From')
        sms = request.args.get('Body')

        if not frm or not sms:
            raise EmptyRequest

        parts = sms.split(maxsplit=1)
        if len(parts)==2: cmd,args = parts
        else: cmd,args = sms,""
        cmd = cmd.lower()

        return cls(frm, cmd, args)


class TBMessage(object):
    def __init__(self, msg, **kwargs):
        self.msg = msg
        self.kwargs = kwargs

    def __str__(self):
        return self.msg

    def asTwiML(self):
        resp = '<Message'
        if 'to' in self.kwargs:
            resp+= ' to="%s">' % self.kwargs['to']
        else:
            resp+='>'
        resp += self.msg[:1500]
        resp += "</Message>"
        return resp


class TBResponse(object):
    def __init__(self):
        self.msgs = []

    def __len__(self):
        return len(self.msgs)

    def addMsg(self, msg, **kwargs):
        self.msgs.append(TBMessage(msg, **kwargs))

    def asTwiML(self):
        assert len(self.msgs) > 0
        resp = '<?xml version="1.0" encoding="UTF-8"?>'
        resp+= "<Response>"
        for m in self.msgs:
            resp+=m.asTwiML()
        resp+= "</Response>"
        return str(resp)

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
        raise AmbiguousAction(search_cmd, '\n'.join([i[0] for i in m]))
    return m[0][1]

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
