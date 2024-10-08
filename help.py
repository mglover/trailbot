from flask import render_template
from .dispatch import routes, cats, tbroute, getAction, UnknownAction

@tbroute('help')
def help(req):
    if not req.args:
        ## This case is handled by Twilio upstream
        return  render_template('help.txt')
    hcmd = req.args

    if hcmd in ('me', 'all', '*'):
        all = [spec for spec,cmd in routes if hasattr(cmd, '_help')]
        return render_template("help_all.txt", all=all)

    hfxn = getAction(hcmd)
    if not hfxn:
        raise UnknownAction(hcmd)

    if hasattr(hfxn, '_help'):
        return hfxn._help
    else:
        return f"Sorry, I don't know anything else about {hcmd}"

