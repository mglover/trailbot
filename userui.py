## import loop with user/dispatch requires these to be in their own file
import re
from flask import render_template
from .core import success, TBError, parseArgs, isBotPhone
from .user import User, needsreg
from .userdata import UserObj
from .dispatch import tbhelp, tbroute
from .response import TBMessage
from .location import Location

@tbroute(re.compile('^@.*$'), cat='chat')
@needsreg("to send direct messages")
def dm(req):
    dstu = req.user.lookup(req.cmd)
    if isBotPhone(dstu.phone):
        #message to a bot
        return dstu.getResponse(req)
    else:
        # message to real phone
        return TBMessage('@%s: %s'%(req.user.handle, req.args),
            to=dstu.phone)


@tbroute('register', cat="settings")
@tbhelp(
"""register -- register a TrailBot @handle

You can say something like:
 'register @YourHandle'
""")
def reg(req):
    u = User.register(req.frm, req.args)
    return render_template('reg.txt', handle=u.handle)


@tbroute('unregister', cat="settings")
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

@tbroute('whoami', cat="settings")
def whoami(req):
    if req.user:
        return "You are @%s" % req.user.handle
    else:
        return "You are not registered"


@tbroute('more', cat="etc")
@tbhelp(
"""more -- continue reading
""")
@needsreg('to continue reading')
def more(req):
    m = req.user.getMore()
    if m: return TBMessage(m, noescape=True)
    else: return "Nothing else to read"

## user data

@tbroute('forget', cat="settings")
@tbhelp(
"""forget -- delete saved data

Related help: 'addr', 'here', 'there'
""")
@needsreg("to use saved data")
def forget(req):
    UserObj.lookup(req.args, req.user).erase()
    return success("'%s' forgotten" % req.args)


@tbroute('share', cat='settings')
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

    UserObj.lookup(nam=nam, requser=req.user).share(spec)

    return success("Shared %s with %s" % (nam, spec))


@tbroute('unshare', cat="settings")
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

    UserObj.lookup(nam, req.user).unshare(spec)

    return success("Unshared %s with %s" % (nam, spec))


@tbroute('address', 'here', 'there', cat="nav")
@tbhelp(
"""addr(ess) -- save any location
here -- save your current location
there -- save your destination

Say something like:
  'addr mom 123 E Main St, City, State'
""")
@needsreg("to use saved data")
def saveloc(req):
    print('req.cmd', req.cmd)
    if req.cmd == 'addr':
        args = req.args.split(maxsplit=1)
    else:
        args = (req.cmd, req.args)

    nam = args[0]
    if len(args) > 1 and args[1]:
        loc = Location.fromInput(args[1], req.user)
        loc.save(nam.lower())
    else:
        print('nam', nam)
        loc = Location.lookup(nam, req.user)
    return render_template("forget.txt", nam=nam.lower(), loc=loc)
