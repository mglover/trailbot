"""
trailbot.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, Response, redirect, abort,Blueprint
import os

import config
from core import *
from user import User, UserDatum, HandleUnknownError, NotRegisteredError
from location import Location
import turns
from wx import wxFromLocation

bp = Blueprint('wx', __name__, '/wx')

##
## TwiML
##


def twiML(content):
    return twiResp(twiMsg(content))

def twiResp(content):
    """ Wrap content in a twiML Response tag"""
    resp = '<?xml version="1.0" encoding="UTF-8"?>'
    resp+= "<Response>"
    resp+= content
    resp+= "</Response>"
    return str(resp)

def twiMsg(msg, to=None):
    resp = '<Message'
    if to:
        resp += ' to="%s">'%to
    else:
        resp += '>'
    resp += msg
    resp += "</Message>"
    return str(resp)

##
## error/auth hooks
##
@bp.errorhandler(500)
def code_fail(error):
    return twiML(
"""I'm sorry, something has gone wrong with my programming.
Try again?  That works sometimes.  I'll let the boss know what happened!"""
   )

@bp.errorhandler(401)
def auth_reqd(error):
    return Response(
        "Authorization Required",
        401,
        {'WWW-Authenticate': 'Basic realm TrailBot'}
    )

def authenticate(request):
    username="twilio"
    password="BananaPudding"
    if not request.authorization \
      or request.authorization.username != username \
      or request.authorization.password != password:
        abort(401)


class RegistrationRequired(TBError):
    msg = \
"""You must register a @handle to %s

To register a handle, choose @YourNewHandle
and say 'reg @YourNewHandle"""



def help(args, frm, user):
    msg = "This is TrailBot, you asked for help?"
    msg+= "\nI understand these commands:"
    msg+= "\nwx, sub, unsub, reg, unreg, status."

    msg+= "\n If you know another person's @handle,"
    msg+= " you can send them a direct message "
    msg+= " by starting your message with @handle"

    msg+= "\nTo view the full documentation, visit"
    msg+= " oldskooltrailgoods.com/trailbot"
    return twiML(msg)


def wx(args, frm, user):
    if len(args):
        loc = Location.fromInput(args, user)
    elif user:
        loc = Location.lookup("here", user)
    if not loc:
        return twiML("Weather report for where?")
    return twiML(wxFromLocation(loc))


def reg(args, frm, user):
            u = User.register(frm, args)
            msg = "Success: @%s registered."%u.handle
            msg+="\n\nTo set your first status update,"
            msg+="\n say 'status Your First Status'"
            msg+= "\nsay 'help' for help"
            return twiML(msg)

def unreg(args, frm, user):
            if not user:
                raise NotRegisteredError
            user.unregister()
            return twiML("Success: @%s unregistered."%user.handle)


def sub(args, frm, user):
            subu = User.lookup(args)
            subu.subscribe(frm)
            msg = "Success: subscribed to @%s." % subu.handle
            msg+="\nTo unsubscribe at any time, say 'unsub @%s'." %\
                subu.handle
            if not user:
                msg+="\n\nTo send a direct message to @%s" % subu.handle
                msg+="\nyou have to register your own @handle."
                msg+="\nSay 'reg @YourNewHandle' to register"
                msg+="\nThen you can say '@%s Yo! sup?'" % subu.handle
                msg+="\nFor help, say 'help'"
            if subu.status:
                msg+="\n\nCurrent status for @%s follows." % subu.handle
                stat = "@%s: %s" % (subu.handle, subu.status)
                return twiResp(twiMsg(msg)+twiMsg(stat))
            else:
                return twiML(msg)


def unsub(args, frm, user):
            subu = User.lookup(args)
            subu.unsubscribe(frm)
            return twiML("Success: unsubscribed from @%s" % subu.handle)

def status(args, frm, user):
            if not args:
                msg = "Err? say status Your new status to set your status"
                msg+= "\nor status @handle to get another user's status"
                return twiML(msg)
            if args.startswith('@'):
                # this is a status request
                u = User.lookup(args)
                if u.status:
                    return twiML("@%s: %s" % (u.handle, u.status))
                else:
                    return twiML("No status for %s" % u.handle)
            else:
                # this is a status update
                status = args
                user.setStatus(status)
                msgs = []
                tmpl = "@%s: %s" % (user.handle, status)
                for pnum in user.subs:
                    msgs.append(twiMsg(tmpl, to=pnum))
                msgs.append(
                    twiMsg("Success: update sent to %d followers" % len(msgs)))
                return twiResp(''.join(msgs))

def whoami(args, frm, user):
            if user:
                return twiML("You are @%s" % user.handle)
            else:
                return twiML("You are not registered")

def where(args, frm, user):
            loc = Location.fromInput(args, user)
            return twiML(loc.toSMS())

def tbt(args, frm, user, mode=None):
            if mode == 'drive': profile='car'
            elif mode == 'bike': profile='bike'

            if user:
                here = Location.lookup("here", user)
                there = Location.lookup("there", user)

            parts = turns.parseRequest(args, ('to', 'from'))
            locs = dict(
                [(k, Location.fromInput(v, user))
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
                msg = "Err? You have to tell me where you're starting from."
                msg+="\nsay 'drive from StartLocation to EndLocation'"
                msg+="\nor say 'here StartLocation'"
                msg+= "\nthen say 'drive to EndLocation'"
                return twiML(msg)
            if not 'to' in locs:
                msg = "Err? You have to tell me where you're going to."
                msg+="\nsay 'drive toEndLocation from StartLocation'"
                msg+="\nor say 'there EndLocation'"
                msg+="\nthen say 'drive from StartLocation'"
            msg = turns.fromLocations(locs['from'], locs['to'], profile)
            return twiML(msg[:1500])

def forget(args, frm, user):
            if not user:
                raise RegistrationRequired("to use saved data")

            user.eraseObj(args)

            msg ="Success: '%s' forgotten" % args
            return twiML(msg)

def saveloc(args, frm, user, cmd=None):
            if not user:
                raise RegistrationRequired("to use saved locations")

            if cmd == 'addr':
                nam, q = args.split(maxsplit=1)
            else:
                nam = cmd
                q = args
            loc = Location.fromInput(q, user)
            user.saveObj(nam.lower(), loc)

            msg= "Success. '%s' is set to:" % nam
            msg+="\n"+loc.toSMS()
            msg+="\n\nTo forget '%s', say 'forget %hs'" % (nam, nam)
            return twiML(msg)

def sharing(args, frm, user, cmd=None):
            if not user:
                raise RegistrationRequiredError('to share data')
            parts = args.split()
            if len(parts) == 1:
                nam = parts[0]
                spec = '*'
            elif len(parts) == 3:
                if  parts[1] != 'with':
                    return twiML("Err?  say '%s thing with @handle'" % cmd)
                else:
                    nam, _, spec = parts

            if cmd == 'share':
                user.shareObj(nam, spec)
                return twiML("Success. Shared %s with %s" % (nam, spec))
            else:
                user.unshareObj(nam, spec)
                return twiML("Success. Unshared %s with %s" % (nam, spec))

def dm(args, frm, user, handle=None):
            if not user:
                raise RegistrationRequired("to send direct messages")
            dstu = User.lookup(handle)
            tmsg= twiMsg('@%s: %s'%(user.handle, args ),
                to=dstu.phone)
            return twiResp(tmsg)



@bp.route("/fetch")
def sms_reply():
    authenticate(request)
    frm = request.args.get('From')
    sms = request.args.get('Body')
    if not frm or not sms:
        return twiML("No request")

    user = User.lookup(frm, raiseOnFail=False)

    try:
        cmd,args = sms.split(maxsplit=1)
    except ValueError:
        cmd = sms
        args= ""

    cmd = cmd.lower()

    try:
        if cmd.startswith('help'):
            return help(args, frm,user)
        elif cmd == 'forget':
            return forget(args, frm, user)
        elif cmd in ('drive', 'bike'):
            return tbt(args, frm, user, mode=cmd)
        elif cmd in ('addr', 'here', 'there'):
            return saveloc(args, frm, user, cmd=cmd)
        elif cmd in ('share', 'unshare'):
            return sharing(args, frm, user, cmd=cmd)
        elif cmd.startswith('@'):
            return dm(args, frm, user, handle=cmd)
        elif cmd == "500":
            abort(500)
        elif cmd =='wx':
            return wx(args, frm,user)
        elif cmd.startswith('reg'):
            return reg(args, frm, user)
        elif cmd.startswith('unreg'):
            return unreg(args, frm, user)
        elif cmd.startswith('sub'):
            return sub(args, frm, user)
        elif cmd.startswith('unsub'):
            return unsub(args, frm ,user)
        elif cmd =='status':
            return status(args, frm, user)
        elif cmd == 'whoami':
            return whoami(args, frm, user)
        elif cmd == 'where':
            return where(args, frm, user)

        else:
            msg ="I don't know how to do %s. \n" % cmd
            msg+="msg 'help' for a list of commands, "
            msg+="or visit oldskooltrailgoods.com/trailbot "
            msg+="to view the full documentation."
            return twiML(msg)

    except TBError as e:
        return twiML(str(e))


