import wikipedia
from requests.exceptions import ConnectionError
from .dispatch import tbroute, tbhelp
from . import netsource


wikipedia.requests = netsource.TBSession


@tbroute('wiki', 'wikipedia', cat="search")
@tbhelp(
'''wiki -- get Wikipedia summary for a topic
    e.g. say 'wiki New York'
    or 'wiki potato pancakes'
''')
def wiki(req):
    try:
        return "From Wikipedia: " + \
            wikipedia.summary(req.args, auto_suggest=False)
    except wikipedia.exceptions.DisambiguationError as e:
        lines = [l for l in str(e).split('\n') if not l.startswith("All pages")]
        ret = "Wikipedia says: %s" % '\n'.join(lines)
        ret+= "\n\ntry again with one of those options"
        return ret
    except wikipedia.exceptions.PageError:
        return "Wikipedia has no information about %s" % req.args
    except ConnectionError:
        return "Wikipedia disconnected without answering.  Try again!"
