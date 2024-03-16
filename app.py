from flask import Flask, abort, request, render_template, url_for, send_from_directory
from flask.views import View

import os, json
from datetime import datetime

import config,smswx
from db import getdb

app = Flask(__name__)
app.TESTING=config.ADMIN

try:
    admin=config.ADMIN
    wx=config.WX
except NameError:
    admin=False
    wx=True

if wx:
    import smswx
    app.register_blueprint(smswx.bp, url_prefix='/wx')

if admin:
    import pricing
    app.register_blueprint(pricing.bp, url_prefix=('/pricing'))


def static(name, path=None):
    if not path: path='/'+name
    def f():
        return render_template(name+'.html')
    app.add_url_rule(path, name, f)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


static('index', '/')
for s in ('bcard', 'smswx', 'footnotes', 'molding', 
    'patterning', 'shoecare', 'weatherbot', 'lessons', 
'turnshoe_syllabus'): static(s)


@app.route('/news')
def news():
    newsdir = os.path.join(config.DB_ROOT, 'news')
    news = os.listdir(newsdir)
    news.sort(reverse=True)
    articles = []
    for n in news:
        f = os.path.join(newsdir, n)
        data = json.load(open(f))
        data['created'] = datetime.fromtimestamp(
            os.stat(f).st_mtime).strftime("%d %B %Y")
        articles.append(data)

    return render_template('news.html', articles=articles)


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


@app.route('/gallery/<gname>')
def gallery(gname):
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

    return render_template('gallery.html', gallery=gallery,
        title=gdata['title'])


@app.route('/gallery')
def gallery_list():
    gdir = os.path.join(config.DB_ROOT, 'galleries')
    gallery = []
    for g in os.listdir(gdir):
        p = getPreview(g)
        if p : gallery.append(p)

    return render_template('gallery.html', gallery=gallery,
        title="Photo Galleries", click="link")

@app.route('/goods')
def goods():
    products = getdb('goods')
    return render_template('goods.html', products=products)

@app.route('/welted')
def welted():
    products = getdb('shoes', '#welted')
    return render_template('welted.html', title='Hiking Boots',
        products=products)

@app.route('/turnshoes')
def turnshoes():
    products = getdb('shoes', '#turn')
    return render_template('turnshoes.html', title='Turnshoes',
        products=products)


if __name__ == '__main__':
    app.run(debug=False)
