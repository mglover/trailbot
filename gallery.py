import config
from flask import abort, url_for
import os, json

def getData(gname):
    gfile = os.path.join(config.DB_ROOT, 'galleries', gname)
    gdata = json.load(open(gfile))
    return gdata

def getPreview(gname):
    try:
        gdata = getData(gname)
    except  json.JSONDecodeError:
        return None
    except FileNotFoundError:
        return None
    if gdata.get('hidden', False):
        return  None
    first_photo = gdata['items'][0][0]
    return  {
        'photo': gdata['items'][0][0], 
        'caption': gdata['title'],
        'link': url_for('gallery', gname=gname)
    }

def getGallery(gname):
    try:
        gdata = getData(gname)
    except FileNotFoundError:
        abort(404)
    gallery = []
    for item in gdata['items']:
        if len(item) < 2:
            # this is a link to another gallery
            p = getPreview(item[0])
            if p:
                gallery.append(p)
        else:
            gallery.append({'photo':item[0], 'caption':item[1]})
    gdata["items"][:] = gallery
    return gdata

