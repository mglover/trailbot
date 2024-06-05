##
## weatherbot
##
from .netsource import NetSource
from .dispatch import tbroute, tbhelp
from .location import Location

class WxSource (NetSource):
    name = "Nat'l Wx Svc"
    baseUrl = 'https://forecast.weather.gov/MapClick.php'
    def makeUrl(self, *args, **kwargs):
        return self.baseUrl

    def makeParams(self, loc, *args, **kwargs):
        return {
            'lat': loc.lat,
            'lon': loc.lon,
            'unit': 0,     # imperial=0, metric=1
            'lg': "english",
            'FcstType': "json"
        }

    def makeResponse(self, *args, days=3):
        """Create a human-readable weather report from NWS JSON
        """
        wxjson = self.content
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

        return rpt

@tbroute('wx', 'weather')
@tbhelp(
"""wx -- get a 3 day weather report from US NWS.

You can say something like:
 'wx New York City' or 
 'wx denver, co'
""")
def wx(req):
    loc = None
    if len(req.args):
        loc = Location.fromInput(req.args, req.user)
    elif req.user:
        loc = Location.lookup("here", req.user)
    if not loc:
        return "Weather report for where?"
    return WxSource(loc, days=3).toSMS()

