import config
from flask import abort, url_for
import os, json

def getData(gname):
    try:
        gfile = os.path.join(config.DB_ROOT, 'galleries', gname)
        gdata = json.load(open(gfile))
    except FileNotFoundError:
        abort(404)
    return gdata

def getPreview(gname):
    try:
        gdata = getData(gname)
    except  json.JSONDecodeError:
        return None
    if gdata.get('hidden', False):
        return  None
    first_photo = gdata['items'][0][0]
    caption = gdata['title']
    link = url_for('gallery', gname=gname)
    return (first_photo,caption, link)

def getGallery(gname):
    gdata = getData(gname)
    title = gdata['title']
    gallery = []
    for item in gdata['items']:
        if len(item) < 2:
            # this is a link to another gallery
            p = getPreview(item[0])
            if p:
                gallery.append(p)
        else:
            gallery.append((item[0], item[1], ''))
    return (gallery, title)

