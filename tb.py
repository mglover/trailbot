"""
trailbot.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, Response, redirect, abort,Blueprint,\
    render_template

from .dispatch import dispatch

bp = Blueprint('wx', __name__, '/wx', template_folder='templates')

## actions
from .help import help
from .wx import wx
from .word import define
from .location import where
from .nav import drive, distance
from .userui import reg, unreg, whoami, saveloc, forget, share, unshare
from .status import sub, unsub, status
from .group import group, ungroup, invite, join, leave, chat

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


@bp.route("/fetch")
def sms_reply():
        authenticate(request)
        return dispatch(request)
