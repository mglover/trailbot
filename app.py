from flask import Flask, request, render_template, url_for
from flask.views import View

import config,smswx
from db import getdb

app = Flask(__name__)
app.TESTING=True

class BasicView(View):
    def __init__(self, template):
        self.template=template+'.html'
    def dispatch_request(self):
        return render_template(self.template)


try:
    admin=config.ADMIN
    wx=config.WX
except NameError:
    admin=False
    wx=True

if wx:
    import smswx
    app.add_url_rule('/wx', view_func=smswx.sms_reply)

if admin:
    import pricing
    app.add_url_rule('/pricing',view_func=pricing.index,
        methods=['POST','GET'])
    app.add_url_rule('/pricing_new',view_func=pricing.new,
        methods=['POST','GET'])

app.add_url_rule('/', view_func=BasicView.as_view('/', 'index'))
for r in ['molding', 'smswx', 'footnotes']:
    app.add_url_rule('/'+r, view_func=BasicView.as_view(r, r))


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
