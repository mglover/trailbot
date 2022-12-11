import csv, os

from flask import Flask, request, render_template, url_for
from flask.views import View

import smswx, config

app = Flask(__name__)
app.TESTING=True


@app.context_processor
def inject_static():
    def static(f):
        return url_for('static', filename=f)
    return dict(static=static)


class BasicView(View):
    def __init__(self, template):
        self.template=template+'.html'
    def dispatch_request(self):
        return render_template(self.template)


app.add_url_rule('/', view_func=BasicView.as_view('/', 'index'))
app.add_url_rule('/wx', view_func=smswx.sms_reply)

for r in ['molding', 'turnshoes', 'welted', 'smswx', 'secret_recipe']:
    app.add_url_rule('/'+r, view_func=BasicView.as_view(r, r))


@app.route('/goods')
def goods():
    db = open(os.path.join(config.DB_ROOT, "goods.csv"))
    products = csv.reader(db)
    return render_template('goods.html', products=products)

if __name__ == '__main__':
    app.run(debug=False)
