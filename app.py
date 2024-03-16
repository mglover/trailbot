from flask import Flask, request, render_template, url_for, send_from_directory
from flask.views import View

import os, json
from datetime import datetime

import config,trailbot
from db import getdb
from gallery import getGallery, getPreview

app = Flask(__name__)
app.TESTING=config.ADMIN

try:
    admin=config.ADMIN
    tb=config.WX
except NameError:
    admin=False
    tb=True

if tb:
    import trailbot
    app.register_blueprint(trailbot.bp, url_prefix='/wx')

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
for s in ('footnotes', 'molding', 
    'patterning', 'shoecare', 'weatherbot', 'trailbot', 'lessons', 
    'turnshoe_syllabus'): static(s)

@app.route('/welted')
def welted():
    print("hello!")
    return render_template('welted.html', args=getGallery('welted'))

@app.route('/turnshoes')
def turnshoes():
    return render_template('turnshoes.html', args=getGallery('turnshoes'))



@app.route('/news')
def news():
    newsdir = os.path.join(config.DB_ROOT, 'news')
    news = os.listdir(newsdir)
    news.sort(reverse=True)
    articles = []
    for n in news:
        f = os.path.join(newsdir, n)
        data = json.load(open(f))
        articles.append(data)

    return render_template('news.html', articles=articles)


@app.route('/gallery')
def gallery_list():
    return render_template('gallery.html',args=getGallery('index'))

    gdir = os.path.join(config.DB_ROOT, 'galleries')
    gallery = []
    dirls = os.listdir(gdir)
    dirls.sort()
    for g in dirls:
        p = getPreview(g)
        if p and  p['toplevel']: gallery.append(p)
    args = {'items':gallery, 'title':"Photo Galleries"}
    return render_template('gallery.html', args=args)


@app.route('/gallery/<gname>')
def gallery(gname):
    args = getGallery(gname)
    return render_template('gallery.html', args=getGallery(gname))

@app.route('/goods')
def goods():
    return render_template('goods.html', args=getGallery('goods'))

if __name__ == '__main__':
    app.run(debug=False)
