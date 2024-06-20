
def escape(str_xml):
    str_xml = str_xml.replace("&", "&amp;")
    str_xml = str_xml.replace("<", "&lt;")
    str_xml = str_xml.replace(">", "&gt;")
    str_xml = str_xml.replace("\"", "&quot;")
    str_xml = str_xml.replace("'", "&apos;")
    return str_xml

def success(msg):
    return "TrailBot: Success: %s" % msg

def isBotPhone(self, phone):
    assert type(phone) is str
    return phone.startswith("+07807")


class TBError(Exception):
    msg = "TBError: '%s'"
    def __init__(self, *args):
        self.args = args
    def __str__(self):
        return self.msg % self.args


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


