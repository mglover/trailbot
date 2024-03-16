## import loop with user/dispatch requires these to be in their own file
import re
from flask import render_template
from .core import success, TBError, parseArgs
from .user import User, needsreg
from .dispatch import tbhelp, tbroute, TBResponse
from .location import Location

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
@needsreg('to unregister')
def unreg(req):
    if not req.user:
        raise RegistrationRequired('to unregister')
    req.user.unregister()
    return success("@%s unregistered." % req.user.handle)

@tbroute('whoami')
def whoami(req):
    if req.user:
        return "You are @%s" % req.user.handle
    else:
        return "You are not registered"


## user data

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
