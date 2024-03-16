"""
trailbot.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, Response, redirect, abort,Blueprint,\
    render_template
import os, re, requests

from . import config
from .core import *
from .dispatch import dispatch, tbroute, tbhelp, TBResponse, getAction

from .location import Location
from .user import User, UserDatum, NotRegisteredError
from .group import Group
from . import nav

bp = Blueprint('wx', __name__, '/wx', template_folder='templates')


class RegistrationRequired(TBError):
    msg = \
"""You must register a @handle %s

To register a handle, choose @YourNewHandle
and say 'reg @YourNewHandle"""


##
## error/auth hooks
##
@bp.errorhandler(500)
def code_fail(error):
    return """I'm sorry, something has gone wrong with my programming.
Try again?  That works sometimes.  I'll let the boss know what happened!"""

def authenticate(request):
    username="twilio"
    password="BananaPudding"
    if not request.authorization \
      or request.authorization.username != username \
      or request.authorization.password != password:
        abort(401)


@bp.errorhandler(401)
def auth_reqd(error):
    return Response(
        "Authorization Required",
        401,
        {'WWW-Authenticate': 'Basic realm TrailBot'}
    )

##
## action decorators
##

def needsreg(reason):
    def fxn(inner):
        def require(req, *args, **kwargs):
            if not req.user:
                raise RegistrationRequired(reason)
            return inner(req, *args, **kwargs)
        return require
    return fxn


##
## actions
##

def success(msg):
    return "TrailBot: Success: %s" % msg

@tbroute('help')
def help(req):
    if req.args:
        hcmd = req.args
        hfxn = getAction(hcmd)
        if not hfxn: raise UnknownCommand(hcmd)
        if hasattr(hfxn, '_help'):
            return hfxn._help
        else:
            return f"Sorry, I don't know anything else about {hcmd}"
    else:
        ## This case is handled by Twilio upstream
        msg = render_template('help.txt')
    return msg



from .wx import wx
from .word import define



@tbroute('register')
@tbhelp(
"""register -- register a TrailBot @handle

You can say something like:
 'register @YourHandle'
""")
def reg(req):
    u = User.register(req.frm, req.args)
    return render_template('reg.txt', handle=u.handle)


@tbroute('unregister')
@tbhelp(
"""unregister -- delete your TrailBot @handle

Say: 'unregister' or 'unreg'

WARNING: this will immediately delete all of your
saved data.  There is no undo!
""")
def unreg(req):
    if not req.user:
        raise NotRegisteredError
    req.user.unregister()
    return success("@%s unregistered." % req.user.handle)


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


@tbroute('whoami')
def whoami(req):
    if req.user:
        return "You are @%s" % req.user.handle
    else:
        return "You are not registered"


@tbroute('where')
@tbhelp(
"""where -- lookup a location

You can say something like:
  'where Empire State Building'
  'where Denver, CO'
  'where Pinnacle Bank, Durango, Colorado'
""")
def where(req):
    loc = Location.fromInput(req.args, req.user)
    return loc.toSMS()


@tbroute('drive')
@tbhelp(
"""drive -- get turn-by-turn directions

You can say something like:
  'drive to San Francisco from Washington, DC'

Related help: 'here', 'there'
""")
def drive(req):
    loc_a, loc_b = nav.getStartEnd(req)
    route = nav.Route(loc_a, loc_b, steps=True)
    return route.toSMS()


@tbroute('distance')
@tbhelp(
"""distance -- get the road distance and travel time

Say something like:
  'distance from Empire State Building to Battery Park'

Related help: 'here', 'there'
""")
def distance(req):
    loc_a, loc_b = nav.getStartEnd(req)
    route = nav.Route(loc_a, loc_b, steps=False)
    return route.toSMS()


@tbroute('forget')
@tbhelp(
"""forget -- delete saved data

Related help: 'addr', 'here', 'there'
""")
@needsreg("to use saved data")
def forget(req):
    req.user.eraseObj(req.args)
    return success("'%s' forgotten" % req.args)


@tbroute('address', 'here', 'there')
@tbhelp(
"""addr(ess) -- save any location
here -- save your current location
there -- save your destination

Say something like:
  'addr mom 123 E Main St, City, State'
""")
@needsreg("to use saved data")
def saveloc(req):
    if req.cmd == 'addr':
        nam, q = req.args.split(maxsplit=1)
    else:
        nam = req.cmd
        q = req.args
    loc = Location.fromInput(q, req.user)

    req.user.saveObj(nam.lower(), loc)

    msg= success("'%s' is set to:" % nam)
    msg+="\n"+loc.toSMS()
    msg+="\n\nTo forget '%s', say 'forget %hs'" % (nam, nam)
    return msg


@tbroute('share')
@tbhelp(
"""share -- share saved data with others

Say something like:
  'share here with @handle
  'share there' to share 'there' with everyone
""")
@needsreg('to share data')
def share(req):
    vals = dict(parseArgs(req.args, {'with'}))
    nam = vals['']
    spec = vals.get('with', '*')

    req.user.shareObj(nam, spec)
    return success("Shared %s with %s" % (nam, spec))


@tbroute('unshare')
@tbhelp(
"""
unshare -- stop sharing saved data with others
Say something like:

  'unshare there'
""")
@needsreg('to share data')
def unshare(req):
    vals = dict(parseArgs(req.args, {'with'}))
    nam = vals['']
    spec = vals.get('with', '*')

    req.user.unshareObj(nam, spec)
    return success("Unshared %s with %s" % (nam, spec))


@tbroute(re.compile('^@.*$'))
@tbhelp(
"""direct messaging
Say:

  '@handle Your Message Goes Here'
""")
@needsreg("to send direct messages")
def dm(req):
    dstu = req.user.lookup(req.cmd)
    resp =TBResponse()
    resp.addMsg('@%s: %s'%(req.user.handle, req.args),
        to=dstu.phone)
    return resp


## -- chat --

@tbroute('group')
@needsreg("to use chat groups")
def group(req):
    flags = req.args.split()
    if len(flags) < 1:
        return "Err? What group do you want to create? say 'group #tag'"
    tag = flags.pop(0)
    Group.create(tag, req.user, *flags)
    return success("Group '%s' created")

@tbroute('ungroup')
@needsreg("to use chat groups")
def ungroup(req):
    if not req.args:
        return "Err? You need to give me a group to remove. Say 'ungroup #tag'"
    g = Group.fromTag(req.args, req.user)
    g.destroy()
    return success("Group '%s' removed")

@tbroute('invite')
@needsreg("to use chat groups")
def invite(req):
    resp = TBResponse()
    parts = dict(parseArgs(req.args, ['to']))
    if '' not in parts:
        return "Err? Invite whom? Say 'invite @handle to @tag'"
    if 'to' not in parts:
        return "Err? Invite to what group? Say 'invite @handle to @tag"
    handle, tag = parts[''], parts['to']
    g = Group.fromTag(tag, req.user)
    to_user = User.lookup(handle)
    g.invite(to_user)
    resp.addMsg(f"@{req.user.handle} has invited you to {tag}." 
        + "say 'join {tag}' to join",
        to=to_user.phone)
    resp.addMsg(success("%s invited to %s" % (handle, tag)))
    return resp

@tbroute('join')
@needsreg("to use chat groups")
def join(req):
    if not req.args:
        return "Err? What group do you want to join?  Say 'join #tag'"
    g = Group.fromTag(req.args, req.user)
    g.join()
    return success("You have joined #%s" % g.tag)

@tbroute('leave')
@needsreg("to use chat groups")
def leave(req):
    g = Group.fromTag(req.args, req.user)
    g.leave()
    return success("You have left #%s" % g.tag)

@tbroute(re.compile('^#.*$'))
@needsreg("to use chat groups")
def chat(req):
    resp = TBResponse()
    g = Group.fromTag(req.cmd, req.user)
    for r in g.getReaders():
        resp.addMsg(f"@{g.nam}: {req.args}", to=r.phone)
    return resp
## --

@bp.route("/fetch")
def sms_reply():
        authenticate(request)
        return dispatch(request)
