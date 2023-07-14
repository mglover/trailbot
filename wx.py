##
## weatherbot
##
from core import proxy
import requests

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
        'southeast': 'SE', 'northeast': 'NE',
        'southwest': 'SW', 'northwest': 'NW',
        'East': 'E', 'West': 'W', 'South': 'S', 'North': 'N',
        'Monday': 'Mon', 'Tuesday': 'Tue', 'Wednesday': 'Wed',
        'Thursday': 'Thu', 'Friday': 'Fri', 'Saturday': 'Sat',
        'Sunday': 'Sun', 'Night': 'PM',
        'thunderstorm': 't-storm', 'Chance of precipitation is': 'PoP'}
    for orig,new in replaces.items():
        rpt = rpt.replace(orig,new)

    return rpt[:1500]


def wxFromLocation(loc):
    try:
        with proxy.get(
            'https://forecast.weather.gov/MapClick.php',
            params = {
                'lat': loc.lat,
                'lon': loc.lon,
                'unit': 0,     # imperial=0, metric=1
                'lg': "english",
                'FcstType': "json"
            }
        ) as resp: return wx_parse(resp.json())

    except requests.ConnectionError:
        return "NWS timed out looking for %s %s" % (loc.lat, loc.lon)

    except requests.JSONDecodeError:
        return "no data for %s %s" % (loc.lat, loc.lon)
