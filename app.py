import csv, os

from flask import Flask, request, render_template, url_for
from flask.views import View

import smswx, config

app = Flask(__name__)
app.TESTING=True

class BasicView(View):
    def __init__(self, template):
        self.template=template+'.html'
    def dispatch_request(self):
        return render_template(self.template)



app.add_url_rule('/', view_func=BasicView.as_view('/', 'index'))
app.add_url_rule('/wx', view_func=smswx.sms_reply)

for r in ['molding', 'smswx', 'secret_recipe','location']:
    app.add_url_rule('/'+r, view_func=BasicView.as_view(r, r))

def getdb(dbnam):
    p = os.path.join(config.DB_ROOT, dbnam+'.csv')
    fd = open(p)
    return csv.reader(fd)

def mkprice(svcs):
    pricing = getdb('shoeprice')
    t=0
    for n,p in pricing:
         if n in svcs: t = t+int(p)
    return t


turn = [
    "Turnshoe Construction",
    "Latigo Insole", 
    "Stitching", "Patternmaking", "Uppers Leather"
]

welt= [
    "Welted Construction",
    "Vegtan Insole", "Vibram Outsole",
    "Stitching", "Patternmaking", "Uppers Leather"
]

derby = ["Craft"]
oxford = ["Craft 2"]
ankle = ["Ankle Boot"]
vegtan = ["Waxed Vegtan"]
heel = ["Heel Stiffener"]
eva = ["EVA Midsole"]
cork = ["Cork Midsole"]


@app.route('/goods')
def goods():
    products = getdb('goods')
    return render_template('goods.html', products=products)

@app.route('/welted')
def welted():
    entry=welt+vegtan+ankle+derby+cork+heel
    products=[
        ('',mkprice(entry),'Welted derby ankle boot','before.jpg')
    ]
    return render_template('welted.html', title='Hiking Boots',
        products=products)

@app.route('/turnshoes')
def turnshoes():
    entry=turn
    products = [
        ('',mkprice(entry),'Low-cut Carolingian','turnshoes_jpg.jpg'),
        ("",mkprice(entry+ankle),'Carolingian ankle boot','trailshoe.jpg'),
        ('',mkprice(entry+derby),'Low-cut derby','turnshoes_liz.jpg'),
        ]
    return render_template('turnshoes.html', title='Turnshoes',
        products=products)


if __name__ == '__main__':
    app.run(debug=False)
