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
from turns import turns
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
## groups
##
def status_update(user, status):
    user.setStatus(status)
    msgs = []
    tmpl = "@%s: %s" % (user.handle, status)
    for pnum in user.subs:
        msgs.append(twiMsg(tmpl, to=pnum))
    msgs.append(twiMsg("Success: update sent to %d followers" % len(msgs)))
    return twiResp(''.join(msgs))



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

    try:
        if cmd.startswith('help'):
            msg = "This is TrailBot, you asked for help?"
            msg+= "\nI understand these commands:"
            msg+= "\nwx, sub, unsub, reg, unreg, status."

            msg+= "\n If you know another person's @handle,"
            msg+= " you can send them a direct message "
            msg+= " by starting your message with @handle"

            msg+= "\nTo view the full documentation, visit"
            msg+= " oldskooltrailgoods.com/trailbot"
            return twiML(msg)

        elif cmd =='wx':
            if not  len(args):
                return twiML("Weather report for where?")
            loc = Location.fromInput(args, user)
            return twiML(wxFromLocation(loc))

        ## registration/subscription

        elif cmd.startswith('reg'):
            u = User.register(frm, args)
            msg = "Success:  @%s registered."%u.handle
            msg+="\n\nTo set your first status update,"
            msg+="\n say 'status Your First Status'"
            msg+= "\nsay 'help' for help"
            return twiML(msg)

        elif cmd.startswith('unreg'):
            if not user:
                raise NotRegisteredError
            user.unregister()
            return twiML("Success: @%s unregistered."%user.handle)

        elif cmd.startswith('sub'):
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

        elif cmd.startswith('unsub'):
            subu = User.lookup(args)
            subu.unsubscribe(frm)
            return twiML("Success: unsubscribed from @%s" % subu.handle)

        elif cmd =='status':
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
                return status_update(user, args)

        elif cmd == 'whoami':
            if user:
                return twiML("You are @%s" % user.handle)
            else:
                return twiML("You are not registered")

        elif cmd.startswith('@'):
            if not user:
                raise RegistrationRequired("to send direct messages")
            dstu = User.lookup(cmd)
            tmsg= twiMsg('@%s: %s'%(user.handle, args ), 
                to=dstu.phone)
            return twiResp(tmsg)

        ## direction/location

        elif cmd == 'where':
            loc = Location.fromInput(args, user)
            return twiML(loc.toSMS())

        elif cmd  in('addr', 'here','there','home'):
            if not user:
                raise RegistrationRequired("to use saved locations")

            if cmd == 'addr':
                nam, q = args.split(maxsplit=1)
            else:
                nam = cmd
                q = args
            loc = Location.fromInput(q, user)
            user.saveBytes(nam, loc.toJson())

            msg= "Success. '%s' is set to:" % nam
            msg+="\n"+loc.toSMS()
            msg+="\n\nTo forget '%s', say 'forget %hs'" % (nam, nam)
            return twiML(msg)

        elif cmd == 'forget':
            if not user:
                raise RegistrationRequired("to use saved data")

            user.eraseData(typ, args)

            msg ="Success: '%s' forgotten" % args
            return twiML(msg)

        elif cmd in ('drive', 'bike'):
            if cmd == 'drive': profile='car'
            elif cmd == 'bike': profile='bike'

            """ BEGIN parsing nightmare"""
            args = ' '+args
            # check all keywords
            points = {
                't':args.find(' to '),
                'f':args.find(' from ')
            }

            # filter only points given
            keys = list(filter(lambda x: points[x] >=0, points.keys()))
            points = dict(zip([points[k] for k in keys], keys))

            #ordered by line position
            ordered = list(points.keys())
            ordered.sort()
            loc = {}
            for i in range(len(ordered)):
                # get the end of the substring
                pos = ordered[i]
                if i <= len(ordered)-2:
                    end = ordered[i+1]
                else:
                    end = len(args)

                if points[pos] == 't':
                    arg = args[pos+4:end]

                elif points[pos] == 'f':
                    arg = args[pos+6:end]

                loc[points[pos]] = Location.fromInput(arg, user)

            if user:
                here = Location.fromInput("here")
                there = Location.fromInput("there")
                home = Location.fromInput("home")

                if 'f' not in loc and here: loc['f'] = here
                if 'f' not in loc  and home: loc['f'] = home
                if 't' not in loc  and there: loc['t'] = there
                if 't' not in loc and home: loc['t']= home
            """ END parsing nightmare"""


            if not 'f' in loc:
                msg = "Err? You have to tell me where you're starting from."
                msg+="\nsay 'drive from StartLocation to EndLocation'"
                msg+="\nor say 'here StartLocation'"
                msg+= "\nthen say 'drive to EndLocation'"
                return twiML(msg)
            if not 't' in loc:
                msg = "Err? You have to tell me where you're going to."
                msg+="\nsay 'drive toEndLocation from StartLocation'"
                msg+="\nor say 'there EndLocation'"
                msg+="\nthen say 'drive from StartLocation'" 
            msg = turns(loc['f'], loc['t'], profile)
            return twiML(msg[:1500])


        else:
            msg ="I don't know how to do %s. \n" % cmd
            msg+="msg 'help' for a list of commands, "
            msg+="or visit oldskooltrailgoods.com/trailbot "
            msg+="to view the full documentation."
            return twiML(msg)

    except TBError as e:
        return twiML(str(e))


