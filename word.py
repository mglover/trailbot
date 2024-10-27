import random, os, json
from urllib.parse import urljoin
from datetime import date, datetime, timedelta
from flask import render_template

from . import config
from .core import randomWord
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
            raise TypeError("Expected list, got %s" % type(self.content))
        else:
            if not len(self.content) or type(self.content[0]) is not dict:
                return "No match for '%s' from %s" % (self.word, self.name)
            d0 = self.content[0]
            return "From %s: %s: %s" % (
                self.name,
                d0["hwi"]["hw"],
                d0['shortdef'][0]
            )

def oldTwotds(maxage=180):
    dbroot = os.path.join(config.DB_ROOT, 'twotd')
    start = date.today() - timedelta(days=maxage)

    old = []
    for f in os.listdir(dbroot):
        y=int(f[0:4])
        m=int(f[4:6])
        d=int(f[6:8])
        if date(y,m,d) > start:
            p = os.path.join(dbroot, f)
            with open(p) as fd:
                w = json.load(fd)
            old.append(w['word'])
    return old


def tournamentWordOfTheDay():
    dbroot = os.path.join(config.DB_ROOT, 'twotd')
    today = date.today()
    dbfile = os.path.join(dbroot, today.strftime("%Y%m%d"))

    data = None

    if os.path.exists(dbfile):
        try:
            data = json.load(open(dbfile))
        except: pass

    if not data:
        data = {}

    if 'word' not in data:
        old = oldTwotds()
        data['word'] = randomWord()
        while len(data['word']) > 5 or data['word'] in old:
            data['word'] = randomWord()

    lookup = DictionarySource(data['word'])
    if 'lookup' not in data:
        if lookup.err:
            data['lookup_err'] = lookup.err
        else:
            if 'lookup_err' in data: del data['lookup_err']
            data['lookup'] = lookup.content

    data['shorttext'] = lookup.makeResponse()

    if data:
        json.dump(data, open(dbfile, 'w'))

    return render_template('twotd.txt', today=today, data=data)


@tbroute('word', cat="search")
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


@tbroute('twl', cat="search")
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


@tbroute('twotd', cat='games')
@tbhelp(
"""Tournament Word of the Day
a 2-5 letter word from the tournament word list
with a definition (when available) from Merriam-Webster
""")
def twotd(req):
    return tournamentWordOfTheDay()
