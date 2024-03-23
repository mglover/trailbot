import wikipedia

from .dispatch import tbroute, tbhelp
from . import netsource


wikipedia.requests = netsource.TBSession


@tbroute('wiki', 'wikipedia')
@tbhelp(
'''wiki -- get Wikipedia summary for a topic 
    e.g. say 'wiki New York'
    or 'wiki potato pancakes'
''')
def wiki(req):
    try:
        return "From Wikipedia: " + wikipedia.summary(req.args)
    except wikipedia.exceptions.DisambiguationError as e:
        return "Wikipedia says: %s" % e