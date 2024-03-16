from flask import Flask, request, render_template, url_for, send_from_directory
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


def getGallery(gname):
    try:
        gfile = os.path.join(config.DB_ROOT, 'galleries', gname)
        return json.load(open(gfile))
    except FileNotFoundError:
        abort(404)

@app.route('/gallery/<gname>')
def gallery(gname):
    data = getGallery(gname)
    return render_template('gallery.html', gallery=data['items'],
        title=data['title'])

@app.route('/gallery')
def metagallery():
    gdir = os.path.join(config.DB_ROOT, 'galleries')
    gallery = []
    for g in os.listdir(gdir):
        data = getGallery(g)
        first_photo = data['items'][0][0]
        caption = data['title']
        link = url_for('gallery', gname=g)
        gallery.append({first_photo,caption, link})
    return render_template('gallery.html', gallery=gallery,
        title="Photo Galleries")

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
