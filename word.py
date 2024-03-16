from . import config
from .netsource import NetSource
from .dispatch import tbroute, tbhelp
from urllib.parse import urljoin

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

@tbroute('word')
@tbhelp(
"""word -- look up a word in a dictionary

You can say something like:
  'word Hello'
  'word brontosaurus'

Related commands: twl
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
