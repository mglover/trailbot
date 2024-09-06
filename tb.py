"""
tb.py

Flask blueprint, command inmports, and entry point for TrailBot
"""
import warnings
from urllib3.connectionpool import InsecureRequestWarning
from flask import request, Response, abort, Blueprint

from . import config
from .dispatch import dispatch
from .twilio import TBMessage

bp = Blueprint('trailbot', __name__, '/wx', template_folder='templates')

## commands
from .help import help
from .menu import menu
from .wx import wx
from .word import define, twl, twotd
from .wiki import wiki
from .location import where
from .nav import drive, distance
from .userdata import my
from .userui import reg, unreg, whoami, saveloc, forget, share, unshare, more
from .status import sub, unsub, status
from .group import group, ungroup, invite, join, leave, chat
from .feed import news
from .when import when
from .fiveword import fiveword

## bots
from .bot import BotMon
from .wordbot import WordBot


# requests run through the local proxy with an unknown cert
warnings.simplefilter(
    "ignore", 
    category=InsecureRequestWarning,
    lineno=1099
)
warnings.simplefilter(
    "ignore", 
    category=InsecureRequestWarning,
    lineno=999
)

##
## error/auth hooks
##
@bp.errorhandler(500)
def code_fail(error):
    return TBMessage("""I'm sorry, something has gone wrong with my programming.
Try again?  That works sometimes.  I'll let the boss know what happened!""").asTwiML()

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

## bot runner CLI
@bp.cli.command('botman')
def botman():
    BotMon(WordBot).run()

