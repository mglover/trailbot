from flask import render_template

from .dispatch import tbroute,tbhelp
from .user import needsreg
from .userdata import UserObj


@tbroute('echo')
def echo(req):
    return req.args


@tbroute('my', cat='settings')
@tbhelp(
"""my -- see your saved information
say:
  'my addrs' to see saved locations
  'my news' to see saved feeds
""")
@needsreg("to use saved data")
def my(req):
    tmap = {'addrs': 'loc', 'news': 'url'}
    if not req.args:
        return "Err? What do you want to see?  Say 'help my' to learn more"

    typ = tmap.get(req.args)
    if typ is None:
        return "I don't know anything about '%s'" % req.args

    objs = UserObj.search(typ=typ, user=req.user)
    return render_template('my.txt', cnam=req.args, objs=objs)
