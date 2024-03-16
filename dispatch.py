import re
from trailbot.user import User
from trailbot.core import TBError

routes = []

class EmptyRequest(TBError):
    msg = "No request"


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
        resp += self.msg
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
            spec_re = re.compile('^'+spec+'$')
            routes.append((spec_re, cmd))
        return cmd
    return fxn


def getAction(search_cmd):
    for spec_re, cmd in routes:
        if spec_re.match(search_cmd): return cmd
    return None

def dispatch(req):
    cmd = getAction(req.cmd)
    if not cmd:
        return None
    return cmd(req)
