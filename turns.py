"""
  turns.py
  comvert location pairs to turn-by-turn driving directions
"""

import json
from urllib.request import urlopen


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

def turnFromStep(step):
    m= step['maneuver']
    return' '.join([
        m['type'],
        m['modifier'],
        step.get('ref', ''),
        step.get('exit', ''),
        distanceFromMeters(step.get('distance'))
    ])

def turnsFromRoute(route, start=None, end=None):
    r0 = route['routes'][0]
    msg= "Turn directions from OSRM"
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

def turns(loc_a, loc_b, profile):
    host = "https://router.project-osrm.org"
    path = "/route/v1/%s/%s;%s" % (
        profile,
        loc_a.toOSRM(),
        loc_b.toOSRM()
    )
    query = "steps=true&overview=false"

    resp = urlopen("%s%s?%s" % (host, path, query))
    if  resp.status != 200:
        raise ValueError(resp.status)

    route = json.load(resp)
    return turnsFromRoute(route, start=loc_a.orig, end=loc_b.orig)

if __name__ == '__main__':
    data = json.load(open('route.json'))
    print(turnsFromRoute(data, 
        start="Gila Hot Springs, NM", 
        end="Farisita, CO")
    )