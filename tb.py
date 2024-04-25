"""
trailbot.py

receive sms requests via twilio
for a given zip code, lat/lon, place name,or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, Response, redirect, abort,Blueprint,\
    render_template

from . import config
from .dispatch import dispatch
from .core import TBMessage
bp = Blueprint('trailbot', __name__, '/wx', template_folder='templates')

from .wordbot import wordbot

## commands
from .help import help
from .wx import wx
from .word import define, twl, twotd
from .wiki import wiki
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
    return TBMessage("""I'm sorry, something has gone wrong with my programming.
Try again?  That works sometimes.  I'll let the boss know what happened!""")

def authenticate(request):
    if not request.authorization \
      or request.authorization.username != config.BASICAUTH_USER \
      or request.authorization.password != config.BASICAUTH_PASS:
        abort(401)


@bp.errorhandler(401)
def auth_reqd(error):
    return Response(
        "Authorization Required",
        401,
        {'WWW-Authenticate': 'Basic realm TrailBot'}
    )


## entry point
@bp.route("/fetch")
def sms_reply():
        authenticate(request)
        return dispatch(request)
