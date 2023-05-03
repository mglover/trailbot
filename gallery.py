import config
from flask import abort, url_for
import os, json

def getData(gname):
    gfile = os.path.join(config.DB_ROOT, 'galleries', gname)
    gdata = json.load(open(gfile))
    return gdata

def itemIsGallery(item):
    return len(item) < 2

def getPreview(gname):
    try:
        gdata = getData(gname)
    except  json.JSONDecodeError:
        return None
    except FileNotFoundError:
        return None
    if gdata.get('hidden', False):
        return  None
    if itemIsGallery(gdata["items"][0]):
        photo = getPreview(gdata["items"][0][0])['photo']
    else:
        photo = gdata['items'][0][0]
    return  {
        'photo': photo,
        'caption': gdata['title'],
        'toplevel': gdata.get('toplevel', True),
        'link': url_for('gallery', gname=gname)
    }

def getGallery(gname):
    try:
        gdata = getData(gname)
    except FileNotFoundError:
        abort(404)
    gallery = []
    for item in gdata['items']:
        if itemIsGallery(item):
            p = getPreview(item[0])
            if p:
                gallery.append(p)
        else:
            gallery.append({'photo':item[0], 'caption':item[1]})
    gdata["items"][:] = gallery
    return gdata

