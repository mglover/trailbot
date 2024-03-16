"""
smswx.py

receive sms requests via twilio
for a given zip code, lat/lon, or AT shelter name
and return the 3 day weather forecast from NWS as TwiML
"""

from flask import Flask, request, redirect, Blueprint
import csv, os, urllib, json

import config

bp = Blueprint('wx', __name__, '/wx')

def wx_parse(wxjson, days=3):
    """Create a human-readable weather report from NWS JSON
    """
    if 'time' not in wxjson: return 'no data'
    labels = wxjson['time']['startPeriodName']

    rpt = "%s\n%s\n" % (
        wxjson['location']['areaDescription'],
        wxjson['creationDateLocal']
    )
    for i in range(days*2):
        rpt+="%s: %s \n\n" % (labels[i], wxjson['data']['text'][i])

    replaces = {'A chance of': 'Chance',
        ' percent':'%', 'around ': '~', ' to ': '-',
        'Southeast': 'SE', 'Northeast': 'NE', 
        'Southwest': 'SW', 'Northwest': 'NW',
        'East': 'E', 'West': 'W', 'South': 'S', 'North': 'N',
        'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
        'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat', 
        'Sunday': 'Sun', 'Night': 'PM',
        'thunderstorm': 't-storm', 'Chance of precipitation is': 'PoP'}
    for orig,new in replaces.items():
        rpt = rpt.replace(orig,new)

    return rpt[:1500]


def wx_by_lat_lon(lat, lon, **kwargs):
    urlbase = "http://forecast.weather.gov/MapClick.php"
    urlargs = dict(lat=lat,
                lon=lon,
                unit=0,     # imperial=0, metric=1
                lg="english", 
                FcstType="json")
    url = urlbase + "?" + urllib.parse.urlencode(urlargs)
    try:
        wxfd = urllib.request.urlopen(url)
        wxjson = json.load(wxfd)
        return wx_parse(wxjson, **kwargs)

    except urllib.error.URLError:
        return "lookup failed for %s %s" % (lat, lon)

    except json.decoder.JSONDecodeError:
        return "no data for %s %s" % (lat, lon)


def wx_by_zip(zip, **kwargs):
    zipfile = os.path.join(config.DB_ROOT,"zipcode.csv")
    zipdb = csv.reader(open(zipfile))
    for row in zipdb:
        if len(row) and row[0]==zip:
            return wx_by_lat_lon(row[3],row[4], **kwargs)
    return "zip code not found: %s" % zip


def wx_by_shelter(snam, **kwargs):
    sheltfile = os.path.join(config.DB_ROOT,"at_shelters.csv")
    sheltdb = csv.reader(open(sheltfile))
    maybes = []
    for row in sheltdb:
        if len(row) and snam.lower() in row[0].lower():
            maybes.append(row)
    if not len(maybes):
        return "no shelter matching '%s'" % snam
    elif len(maybes) > 1:
        return "multiple matches for %s:"%snam \
            + ', '.join(m[0] for m in maybes)
    else:
        s = maybes[0]
        return "Shelter: %s.\n"%s[0] \
            + wx_by_lat_lon(s[30], s[31], **kwargs)

def twiML(content):
    """Wrap content in TwiML"""
    resp = '<?xml version="1.0" encoding="UTF-8"?>'
    resp+= "<Response>"
    resp+= "<Message>"
    resp+= content
    resp+= "</Message>"
    resp+= "</Response>"
    return str(resp)

def isfloat(s):
    try:
        float(s)
        return True
    except:
        return False


@bp.route("/fetch")
def sms_reply():
    frm = request.args.get('From')
    sms = request.args.get('Body')
    if not frm or not sms:
        return twiML("No request")
    parts = sms.split()
    if not parts:
        return twiML("No request body")
    elif  parts[0] != 'wx':
        return twiML("Bad Request")
    elif len(parts) < 2:
        return twiML("No args")
    elif len(parts) >= 2 and len(parts[1])==5 and parts[1].isdigit():
        zip = parts[1]
        return twiML(wx_by_zip(zip))
    elif len(parts) >= 3 and isfloat(parts[1]) and isfloat(parts[2]):
        lat = parts[1]
        lon = parts[2]
        return twiML(wx_by_lat_lon(lat, lon))
    else:
        return twiML(wx_by_shelter(' '.join(parts[1:])))


if __name__ == "__main__":
    app.run(debug=False)
