from .dispatch import tbroute, routes, cats
import re

@tbroute('menu')
def menu(req):
    msg =  "%d commands in %d catetories:\n" % (len(routes), len(cats))
    for c,v in cats.items():
        msg+= "\n%s: " % c 
        for pats, fxn in v:
            for pat in pats:
                if type(pat) is re.Pattern:
                    p = pat.pattern
                else:
                    p = pat
                msg+= '\n\t%s' % p 
    return msg