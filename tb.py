"""
tb.py

Flask blueprint, command inmports, and entry point for TrailBot
"""
import warnings
from urllib3.connectionpool import InsecureRequestWarning
from flask import request, Response, abort, Blueprint

from . import config
from .dispatch import flask_dispatch
from .response import TBMessage
from .twilio import twiMLfromMessage

bp = Blueprint('trailbot', __name__, '/wx', template_folder='templates')

## commands
from .help import help
from .menu import menu
from .wx import wx
from .word import define, twl, twotd
from .wiki import wiki
from .location import where
from .nav import drive, distance
from .userui import reg, unreg, whoami, saveloc, forget, share, unshare, more
from .status import sub, unsub, status
from .group import group, ungroup, invite, join, leave, chat
from .feed import news
from .when import when, tz, untz, now
from .cal import cal
from .fiveword import fiveword
from .shell import echo, my

## cron daemon
from .cron import CronBot
from .wordbot import WordBot

WordBot()

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
    err = """I'm sorry, something has gone wrong with my programming.
Try again?  That works sometimes.  I'll let the boss know what happened!"""
    return twiMLfromMessage(TBMessage(err))

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
    return flask_dispatch(request)


@bp.cli.command('cron')
def cron():
    CronBot().run()
