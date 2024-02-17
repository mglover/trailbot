def success(msg):
    return "TrailBot: Success: %s" % msg

class TBError(Exception):
    msg = "TBError: '%s'"
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return self.msg % self.args


class TBMessage(object):
    def __init__(self, msg, **kwargs):
        self.msg = msg
        self.kwargs = kwargs

    def __str__(self):
        return self.msg

    def asTwiML(self):
        resp = '<Message'
        if 'to' in self.kwargs:
            resp+= ' to="%s">' % self.kwargs['to']
        else:
            resp+='>'
        resp += self.msg[:1500]
        resp += "</Message>"
        return resp

class TBResponse(object):
    def __init__(self):
        self.msgs = []

    def __len__(self):
        return len(self.msgs)

    def addMsg(self, msg, **kwargs):
        self.msgs.append(TBMessage(msg, **kwargs))

    def asTwiML(self):
        assert len(self.msgs) > 0
        resp = '<?xml version="1.0" encoding="UTF-8"?>'
        resp+= "<Response>"
        for m in self.msgs:
            resp+=m.asTwiML()
        resp+= "</Response>"
        return str(resp)

def parseArgs(args, keywords):
    """ search the request for values separated by keywords 
        return a dict of keyword, value pairs.
    """

    # find the first occasion of each keyword, create a sorted
    # (offset, keyword) list
    args = ' '+args
    keywords = [ ' '+k.strip()+' ' for k in keywords ]
    keylocs = [
        (args.find(k), k)
        for k in keywords
        if args.find(k)>=0]
    keylocs.sort()

    if not len(keylocs):
        return [('', args.strip())]

    first_loc = keylocs[0][0]

    values = []
    if first_loc > 0:
        # there's text before the first keyword
        values.append(( '', args[0:first_loc].strip() ))

    for i in range(len(keylocs)):
        # list is (offset, keyword
        start, kw = keylocs[i]
        start += len(kw)

        # get the end of the substring
        if i <= len(keylocs)-2:
            end = keylocs[i+1][0]
        else:
            end = len(args)

        values.append((kw.strip(), args[start:end]))
    return values


