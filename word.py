import random, datetime, os
from urllib.parse import urljoin

from . import config
from .netsource import NetSource
from .dispatch import tbroute, tbhelp

from .db.TWL06 import twl as twl_mod

class DictionarySource (NetSource):
    # dictionary and thesaurus access
    # via Merriam-Webster dictionaryapi.com
    name = "Merriam-Webster's Collegiate Dictionary"
    baseUrl = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
    apiKey = config.MWD_API_KEY

    def makeUrl(self, word, *args, **kwargs):
        self.word = word
        return urljoin(self.baseUrl, word)


    def makeParams(self, *args, **kwargs):
        params = kwargs.get('params',{})
        params.update({'key': self.apiKey})
        return params

    def makeResponse(self, *args, **kwargs):
        if type(self.content) is not list:
            raise TypeError("Expected list, got %s" % type(res.content))
        else:
            if not len(self.content) or type(self.content[0]) is not dict:
                return "No match for '%s' from %s" % (self.word, self.name)
            d0 = self.content[0]
            return "From %s: %s: %s" % (
                self.name,
                d0["hwi"]["hw"],
                d0['shortdef'][0]
            )

def tournamentWordOfTheDay():
    def randomWord():
        word = ''
        next = ''
        while next != '$':
            word += next
            next = random.choice(twl_mod.children(word))
        return word

    dbroot = os.path.join(config.DB_ROOT, 'twotd')
    today = datetime.date.today()
    dbfile = os.path.join(dbroot, today.strftime("%Y%m%d"))

    if os.path.exists(dbfile):
        return open(dbfile).read()

    word = randomWord()
    while len(word) > 5:
        word = randomWord()

    lookup = DictionarySource(word)
    if lookup.err:
        means = lookup.err
    else:
        means = lookup.content

    today_human = today.strftime('%A, %d %B')
    msg = f"Tournament Word of the Day for {today_human}"
    msg+= f"\n {word}"
    msg+= f"\n\n{means}"
    open(dbfile,'w').write(msg)
    return msg


@tbroute('word')
@tbhelp(
"""word -- look up a word in a dictionary

You can say something like:
  'word Hello'
  'word brontosaurus'

Related commands: twl twotd
""")
def define(req):
    w = req.args
    if not w: return "Which word should I define?"
    return DictionarySource(w).toSMS()


@tbroute('twl')
@tbhelp(
"""twl -- look up word in Tournament Word List

Say 'twl word' or 'twl asdf'

Related commands: word
""")
def twl(req):
    w = req.args
    if twl_mod.check(w):
        return f"YES. '{w}' is a valid word"
    else:
        return f"NO. '{w}' is not a valid word"


@tbroute('twotd')
@tbhelp(
"""Tournament Word of the Day
a 2-5 letter word from the tournament word list
with a definition (when available) from Merriam-Webster
""")
def twotd(req):
    return tournamentWordOfTheDay()
