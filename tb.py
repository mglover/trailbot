"""
trailbot.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, Response, redirect, abort,Blueprint
import os, re

from . import config
from .core import *
from .dispatch import dispatch, tbroute, TBResponse, getAction

from .location import Location
from .wx import wxFromLocation
from .user import User, UserDatum, NotRegisteredError
from . import nav

bp = Blueprint('wx', __name__, '/wx')


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


def tbhelp(helpmsg):
    def fxn(cmd, *args, **kwargs):
        cmd._help = helpmsg
        return cmd
    return fxn

##
## actions
##

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
        msg = "This is TrailBot, you asked for help?"
        msg+= "\nI understand these commands:"
        msg+= "\nwx, sub, unsub, reg, unreg, status."

        msg+= "\n If you know another person's @handle,"
        msg+= " you can send them a direct message "
        msg+= " by starting your message with @handle"

        msg+= "\nTo view the full documentation, visit"
        msg+= " oldskooltrailgoods.com/trailbot"
    return msg

@tbroute('wx', 'weather')
@tbhelp(
"""wx -- get a 3 day weather report from US NWS.

You can say something like:
 'wx New York City' or 
 'wx denver, co'
""")
def wx(req):
    loc = None
    if len(req.args):
        loc = Location.fromInput(req.args, req.user)
    elif req.user:
        loc = Location.lookup("here", req.user)
    if not loc:
        return "Weather report for where?"
    return wxFromLocation(loc)

@tbroute('register')
@tbhelp(
"""register -- register a TrailBot @handle

You can say something like:
 'register @YourHandle'
""")
def reg(req):
    u = User.register(req.frm, req.args)
    msg = "Success: @%s registered."%u.handle
    msg+="\n\nTo set your first status update,"
    msg+="\n say 'status Your First Status'"
    msg+= "\nsay 'help' for help"
    return msg

@tbroute('unregister')
@tbhelp(
"""unregister -- delete your TrailBot @handle

Say: 'unregister' or 'unreg'

WARNING: this will immediately delete all of your 
subscriptionsand saved data.  There is no undo!
""")
def unreg(req):
    if not req.user:
        raise NotRegisteredError
    req.user.unregister()
    return "Success: @%s unregistered." % req.user.handle

@tbroute('subscribe')
@tbhelp(
"""sub(scribe) -- subscribe to a @handle's status updates

Say: 'subscribe @SomeBody'
To unsubscribe, say: 'unsubscribe @SomeBody'
""")
def sub(req):
    subu = User.lookup(req.args)
    subu.subscribe(req.frm)

    resp = TBResponse()

    msg = "Success: subscribed to @%s." % subu.handle
    msg+="\nTo unsubscribe at any time, say 'unsub @%s'." %\
        subu.handle
    if not req.user:
        msg+="\n\nTo send a direct message to @%s" % subu.handle
        msg+="\nyou have to register your own @handle."
        msg+="\nSay 'reg @YourNewHandle' to register"
        msg+="\nThen you can say '@%s Yo! sup?'" % subu.handle
        msg+="\nFor help, say 'help'"
    if subu.status:
        msg+="\n\nCurrent status for @%s follows." % subu.handle

    resp.addMsg(msg)
    if subu.status:
        resp.addMsg("@%s: %s" % (subu.handle, subu.status))

    return resp

@tbroute('unsubscribe')
def unsub(req):
    subu = User.lookup(req.args)
    subu.unsubscribe(req.frm)
    return "Success: unsubscribed from @%s" % subu.handle

@tbroute('status')
@tbhelp(
"""status -- check or set a status update

To check a @handle's status, say: 'status @handle'

To set your status, say something like:
'status Wow what a week! Monday was just...'
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
            return "@%s: %s" % (u.handle, u.status)
        else:
            return "No status for %s" % u.handle
    else:
        # this is a status update
        status = req.args
        req.user.setStatus(status)
        resp = TBResponse()
        tmpl = "@%s: %s" % (req.user.handle, status)
        for pnum in req.user.subs:
            resp.addMsg(tmpl, to=pnum)
        resp.addMsg("Success: update sent to %d followers" % len(resp))
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
'where Portland, Maine'
'where Pinnacle Bank, Durango'
'where 1600 Pennsylania Ave, Washington, DC'

""")
def where(req):
    loc = Location.fromInput(req.args, req.user)
    return loc.toSMS()

class NavMissingFrom(TBError):
    msg = "Err? You have to tell me where you're starting from."
    msg+="\nsay 'drive from StartLocation to EndLocation'"
    msg+="\nor say 'here StartLocation'"
    msg+= "\nthen say 'drive to EndLocation'"

class NavMissingTo(TBError):
    msg = "Err? You have to tell me where you're going to."
    msg+="\nsay 'drive toEndLocation from StartLocation'"
    msg+="\nor say 'there EndLocation'"
    msg+="\nthen say 'drive from StartLocation'"

def getStartEnd(req):
    if req.user:
        here = Location.lookup("here", req.user)
        there = Location.lookup("there", req.user)
    else:
        here = None
        there = None

    parts = nav.parseRequest(req.args, ('to', 'from'))
    locs = dict(
        [(k, Location.fromInput(v, req.user))
            for k,v in parts
            if len(v.strip())
    ])

    if '' in locs and 'to' not in locs:
        locs['to'] = locs['']
    elif '' in locs and 'from' not in locs:
        locs['from'] = locs['']

    if 'from' not in locs and here: locs['from'] = here
    if 'to' not in locs and there: locs['to'] = there

    if not 'from' in locs:
        raise NavMissingFrom

    if not 'to' in locs:
        raise NavMissingTo

    return (locs['from'], locs['to'])

@tbroute('drive', 'bike', 'distance')
def tbt(req):
    if req.cmd == 'drive': profile='car'
    elif req.cmd == 'bike': profile='bike'
    else: profile="car"

    loc_a, loc_b = getStartEnd(req)

    if req.cmd == 'distance':
        msg = nav.distance(loc_a, loc_b, profile)
    else:
        msg = nav.fromLocations(loc_a, loc_b, profile)
    return msg[:1500]

@tbroute('forget')
@needsreg("to use saved data")
def forget(req):
    req.user.eraseObj(req.args)

    msg ="Success: '%s' forgotten" % req.args
    return msg

@tbroute('address', 'here', 'there')
@needsreg("to use saved data")
def saveloc(req):
    if req.cmd == 'addr':
        nam, q = req.args.split(maxsplit=1)
    else:
        nam = req.cmd
        q = req.args
    loc = Location.fromInput(q, req.user)
    req.user.saveObj(nam.lower(), loc)

    msg= "Success. '%s' is set to:" % nam
    msg+="\n"+loc.toSMS()
    msg+="\n\nTo forget '%s', say 'forget %hs'" % (nam, nam)
    return msg

@tbroute('share','unshare')
@needsreg('to share data')
def sharing(req):
    parts = req.args.split()
    if len(parts) == 1:
        nam = parts[0]
        spec = '*'
    elif len(parts) == 3:
        if  parts[1] != 'with':
            return "Err?  say '%s thing with @handle'" % cmd
        else:
            nam, _, spec = parts

    if req.cmd == 'share':
        req.user.shareObj(nam, spec)
        return "Success. Shared %s with %s" % (nam, spec)
    else:
        req.user.unshareObj(nam, spec)
        return "Success. Unshared %s with %s" % (nam, spec)

@tbroute(re.compile('^@.*$'))
@needsreg("to send direct messages")
def dm(req):
    dstu = req.user.lookup(req.cmd)
    resp =TBResponse()
    resp.addMsg('@%s: %s'%(req.user.handle, req.args),
        to=dstu.phone)
    return resp


@bp.route("/fetch")
def sms_reply():
    authenticate(request)
    return dispatch(request)
