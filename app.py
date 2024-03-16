from flask import Flask, request, render_template, url_for, send_from_directory
from flask.views import View

import os.path

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

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    print(app)
    return render_template('index.html')

@app.route('/smswx')
def weatherbot():
    return render_template('smswx.html')

@app.route('/footnotes')
def footnotes():
    return render_template('footnotes.html')

@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/molding')
def molding():
    return render_template('molding.html')

@app.route('/shoecare')
def newshoes():
    return render_template('shoecarea.html')

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
