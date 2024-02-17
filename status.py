from flask import render_template
from .core import success, TBResponse
from .dispatch import tbhelp, tbroute
from .user import User


@tbroute('subscribe')
@tbhelp(
"""sub(scribe) -- subscribe to a @handle's status updates

Say: 'subscribe @handle'
Related help: 'unsubscribe'
""")
def sub(req):
    subu = User.lookup(req.args)
    subu.subscribe(req.frm)

    resp = TBResponse()
    resp.addMsg(success(render_template('sub.txt', subu=subu, user=req.user)))
    if subu.status:
        resp.addMsg("@%s: %s" % (subu.handle, subu.status))

    return resp


@tbroute('unsubscribe')
@tbhelp(
"""unsub(scribe) -- unsubcribe from status updates for a @handle

Say: 'unsub @handle'
""")
def unsub(req):
    subu = User.lookup(req.args)
    subu.unsubscribe(req.frm)
    return success("unsubscribed from @%s" % subu.handle)


@tbroute('status')
@tbhelp(
"""status -- check or set a status update

To check @handle's status, say: 'status @handle'

To set your status, say something like:
'status Wow what a week!'
""")
def status(req):
    if not req.args:
        msg = "Err? say status Your new status to set your status"
        msg+= "\nor status @handle to get another user's status"
        return msg
    if req.args.startswith('@'):
        # this is a status request
        u = User.lookup(req.args)
        if u.status:
            return "TrailBot: status for @%s: %s" % (u.handle, u.status)
        else:
            return "No status for %s" % u.handle
    else:
        # this is a status update
        status = req.args
        req.user.setStatus(status)
        resp = TBResponse()
        tmpl = "TrailBot: update from @%s: %s" % (req.user.handle, status)
        for pnum in req.user.subs:
            resp.addMsg(tmpl, to=pnum)
        resp.addMsg(success("update sent to %d followers" % len(resp)))
        return resp

