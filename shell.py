from .dispatch import tbroute,tbhelp

@tbroute('echo')
def echo(req):
    return req.args