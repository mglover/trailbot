from flask import Flask, request, render_template, url_for, send_from_directory
from flask.views import View

import os, json

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
        data['created'] = os.stat(f).st_ctime
        data['updated'] = os.stat(f).st_mtime
        articles.append(data)

    return render_template('news.html', articles=articles)

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
