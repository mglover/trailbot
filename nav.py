"""
  turns.py
  comvert location pairs to turn-by-turn driving directions
"""
from .core import proxy

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

def fromRoute(route, start=None, end=None):
    r0 = route['routes'][0]
    msg= "Turn directions courtesy OSRM"
    msg+="\nfrom %s\nto %s" % (start, end)

    msg+="\n%s: %s" % (
        distanceFromMeters(r0['distance']),
        durationFromSeconds(r0['duration'])
    )
    for leg in r0['legs']:
        if 'summary' in leg:
            msg+="\nvia %s\n\n" % leg['summary']
        msg+='\n'.join([turnFromStep(s) for s in leg['steps']])
        return msg

def  makeURL(loc_a, loc_b, profile):
    path = "/route/v1/%s/%s;%s" % (
        profile,
        loc_a.toOSRM(),
        loc_b.toOSRM()
    )
    return "https://router.project-osrm.org"+path

def getResponse(url, query):
    with proxy.get(url, params=query) as resp:
        if  resp.status_code != 200:
            raise ValueError(resp.status, resp.body)
        return resp.json()

def fromLocations(loc_a, loc_b, profile):
    url = makeURL(loc_a, loc_b, profile)
    route = getResponse(url,{"steps":"true", "overview":"false"})
    return fromRoute(route, start=loc_a.orig, end=loc_b.orig)

def distance(loc_a, loc_b, profile):
    url = makeURL(loc_a, loc_b, profile)
    route = getResponse(url,{"steps":"false", "overview":"false"})
    return fromRoute(route, start=loc_a.orig, end=loc_b.orig)

def parseRequest(req, keywords):
        """ search the request for values separated by keywords 
            return a dict of keyword, value pairs.
        """

        # find the first occasion of each keyword, create a sorted
        # (offset, keyword) list
        req = ' '+req
        keywords = [ ' '+k.strip()+' ' for k in keywords ]
        keylocs = [
            (req.find(k), k)
            for k in keywords
            if req.find(k)>=0]
        keylocs.sort()

        if not len(keylocs):
            return [('', req.strip())]

        first_loc = keylocs[0][0]

        values = []
        if first_loc > 0:
            # there's text before the first keyword
            values.append(('',req[0:first_loc]))

        for i in range(len(keylocs)):
            # list is (offset, keyword
            start, kw = keylocs[i]
            start += len(kw)

            # get the end of the substring
            if i <= len(keylocs)-2:
                end = keylocs[i+1][0]
            else:
                end = len(req)

            values.append((kw.strip(), req[start:end]))
        return values
