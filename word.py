from .netsource import NetSource
from urllib.parse import urljoin

class DictionarySource (NetSource):
    # dictionary and thesaurus access
    # via Merriam-Webster dictionaryapi.com
    name = "Merriam-Webster's Collegiate Dictionary"
    baseUrl = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"
    apiKey = "f6a35c0b-3b80-4a29-b94c-e6e2903ab276"

    def makeUrl(self, path, *args, **kwargs):
        return urljoin(self.baseUrl, path)


    def makeParams(self, *args, **kwargs):
        params = kwargs.get('params',{})
        params.update({'key': self.apiKey})
        return params


def define(word):
    if not word: return "Which word should I define?"
    res = DictionarySource(word)
    if res.err:
        raise ValueError(res)
        return res.err
    elif type(res.content) is not list:
        raise TypeError("Expected list, got %s" % type(res.content))
    else:
        if not len(res.content) or type(res.content[0]) is not dict:
            return "No match for '%s' from %s" % (word, res.name)
        d0 = res.content[0]
        return "From %s: %s: %s" % (
            res.name,
            d0["hwi"]["hw"],
            d0['shortdef'][0]
        )

"""for later

class ThesauruSource(NetSource):
    baseUrl = ""
    apiKey="ca821a6d-e983-49ee-82dc-1ec99a13c5ac"


def synonym(word):
    pass

"""