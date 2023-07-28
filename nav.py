"""
  nav.py
  comvert location pairs to turn-by-turn driving directions
"""
from .core import TBError, parseArgs, proxy

class NavMissingFrom(TBError):
    msg = "Err? You have to tell me where you're starting from."
    msg+="\nsay 'drive from StartLocation to EndLocation'"
    msg+="\nor say 'here StartLocation'"
    msg+= "\nthen say 'drive to EndLocation'"

class NavMissingTo(TBError):
    msg = "Err? You have to tell me where you're going to."
    msg+="\nsay 'drive toEndLocation from StartLocation'"
    msg+="\nor say 'there EndLocation'"
    msg+="\nthen say 'drive from StartLocation'"


## conversions and unpacking

def distanceFromMeters(m):
    miles = m/1609.344
    if miles < 1:
        yards = int(m*1.09)
        return "%d yards" % yards
    else:
        return '%0.1d miles' % miles

def durationFromSeconds(sec):
    hours = int(sec/3600)
    min = int(sec%3600/60)
    return '%dhr, %dmin' % (hours, min)

def turnFromStep(step, last_step=None):
    typ = step['maneuver']['type']
    mod =  step['maneuver'].get('modifier', '')
    dist = distanceFromMeters(step.get('distance'))

    if step.get('ref'):
        if step.get('name'):
            nam = "%s (%s)" % (step['ref'], step['name'])
        else:
            nam = step['ref']
    elif step.get('name'):
        nam = step['name']
    else:
        nam = 'unnamed road'

    if typ == 'arrive':
        msg =  "Reach destination"

    elif typ == 'depart':
        msg = "Start on %s" % (nam)

    elif typ == 'new name':
        msg = "Continue on %s" % nam

    elif typ == 'turn':
        msg = "Turn %s on %s" % (mod, nam)

    elif typ == 'fork':
         msg = "At the fork, go %s on %s" % (mod, nam)

    elif typ == 'off ramp':
        msg = "Take a %s onto the off ramp" % mod
        if step.get('exits'):
            msg+=" for exit %s" % step['exits']

    elif typ == 'on ramp':
        msg = "Turn %s onto the on ramp" % mod

    elif typ == 'merge':
        msg = "Merge %s onto %s" % (mod, nam)

    else:
        msg=' '.join([typ, mod, nam])

    if step.get('destinations'):
        msg+=" toward %s" % step['destinations']

    if typ != "arrive":
        msg+= " for %s" % dist

    return msg


class Route(object):
    baseurl = "https://router.project-osrm.org"
    source = "OSRM"
    params = {'overview': 'false', 'steps': 'false'}

    def __init__(self, *locations, **params):
        assert len(locations) == 2
        self.locs = locations

        params = dict([
            (k, str(v).lower())
            for k,v in params.items()
            if type(v) in (bool,str)
        ])
        self.params.update(params)
        self.profile = "car"

        path = "/route/v1/%s/%s;%s" % (
            self.profile,
            self.locs[0].toOSRM(),
            self.locs[1].toOSRM()
        )
        url = self.baseurl+path

        with proxy.get(url, params=self.params) as resp:
            if  resp.status_code != 200:
                raise ValueError(resp)
            self.route =  resp.json()


    def toSMS(self):
        r0 = self.route['routes'][0]
        get_steps = self.params['steps'] == 'true'

        if get_steps:
            pre = "Driving directions"
        else:
             pre = "Distance"
        pre+= " courtesy %s" % self.source

        msg= pre + "\nfrom %s\nto %s" % (self.locs[0].orig, self.locs[1].orig)

        msg+="\n%s: %s" % (
            distanceFromMeters(r0['distance']),
            durationFromSeconds(r0['duration'])
        )
        if get_steps:
            for leg in r0['legs']:
                if 'summary' in leg:
                    msg+="\nvia %s\n\n" % leg['summary']
                msg+='\n'.join([turnFromStep(s) for s in leg['steps']])
        return msg



from .location import Location
def getStartEnd(req):
    if req.user:
        here = Location.lookup("here", req.user)
        there = Location.lookup("there", req.user)
    else:
        here = None
        there = None

    parts = parseArgs(req.args, ('to', 'from'))
    locs = dict(
        [(k, Location.fromInput(v, req.user))
            for k,v in parts
            if len(v.strip())
    ])

    if '' in locs and 'to' not in locs:
        locs['to'] = locs['']
    elif '' in locs and 'from' not in locs:
        locs['from'] = locs['']

    if 'from' not in locs and here: locs['from'] = here
    if 'to' not in locs and there: locs['to'] = there

    if not 'from' in locs:
        raise NavMissingFrom

    if not 'to' in locs:
        raise NavMissingTo

    return (locs['from'], locs['to'])
