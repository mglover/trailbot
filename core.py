"""
    NO trailbot includes!
    wrap includes with try/except
"""

try:
    import random
    from .db.TWL06 import twl

    def randomWord():
        word = ''
        next = ''
        while next != '$':
            word += next
            next = random.choice(twl.children(word))
        return word

    def shapedRandomWord(maxlen=None, minlen=None, pluratten=0.5):
        done = False
        while not done:
            word = randomWord()
            if maxlen and len(word) > maxlen: continue
            if minlen and len(word) < minlen: continue
            if word.endswith('s') and random.random() < pluratten: continue
            done = True
        return word

except ImportError as e:
    print (e)


def escape(str_xml):
    str_xml = str_xml.replace("&", "&amp;")
    str_xml = str_xml.replace("<", "&lt;")
    str_xml = str_xml.replace(">", "&gt;")
    str_xml = str_xml.replace("\"", "&quot;")
    str_xml = str_xml.replace("'", "&apos;")
    return str_xml

def success(msg):
    return "TrailBot: Success: %s" % msg

def isBotPhone(phone):
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


