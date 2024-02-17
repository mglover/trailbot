from flask import render_template
from .dispatch import tbroute, getAction, UnknownAction

@tbroute('help')
def help(req):
    if req.args:
        hcmd = req.args
        hfxn = getAction(hcmd)
        if not hfxn: raise UnknownAction(hcmd)
        if hasattr(hfxn, '_help'):
            return hfxn._help
        else:
            return f"Sorry, I don't know anything else about {hcmd}"
    else:
        ## This case is handled by Twilio upstream
        msg = render_template('help.txt')
    return msg
