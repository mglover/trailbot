from flask import request, redirect, render_template,url_for, Blueprint
from db import Column, Component, Product, usd
from dbhtml import Form

bp = Blueprint('pricing', __name__, url_prefix='/pricing')

class View(object):
    vcols = []
    def __init__(self, table, rows=None):
        self.table = table
        self.cols = self.table.cols + self.vcols
        self.rows = []
        if rows:
            for row in rows: self.append(row)

    @classmethod
    def fromTable(cls, table):
        rows = table.select()
        return cls(table, rows)

    @classmethod
    def compute(cls, row):
        return row

    def append(self, row):
        newrow = self.compute(row)
        newrow.idx = len(self.rows)
        self.rows.append(self.compute(newrow))

    def groupByIndex(self, idx):
        groups = {}
        for row in self.rows:
            key = row.data[idx]
            if key not in groups: groups[key] = self.__class__(self.table)
            groups[key].append(row)
        return groups

    def groupBy(self, colnam):
        return self.groupByIndex(self.table.colidx(colnam))


class PricingView(View):
    vcols = [
        Column('Price Each', usd, 'computed'),
        Column('Subtotal', usd, 'computed')
    ]
    @classmethod
    def compute(cls, row):
        pnam,compo,cnt = row.data[:3]
        ea = compo.price()
        subt = usd(ea * cnt)
        row.data = (pnam,compo,cnt,ea,subt)
        return row

    def footer(self):
        return ('Total','','',usd(self.total()))

    def total(self):
        return sum([x.data[4] for x in self.rows])


@bp.route('/', methods=('GET','POST'))
def index():
    Component.load()
    Product.load()

    if request.method == 'POST':
        Component.updateFromPostData(request.form)
        Product.updateFromPostData(request.form)

    return render_template('pricing.html',
        form=Form,
        components=View.fromTable(Component),
        pricing=PricingView.fromTable(Product))

@bp.route('/new', methods=('GET', 'POST'))
def new():
    Component.load()
    Product.load()

    if request.method == 'POST':
        Product.updateFromPostData(request.form)
        Product.save()
        redirect(url_for('pricing.index'))
        return

    pnam = request.args.get('pnam')

    product = View(Product, [Product(data={"Product":pnam})]*6)
    for c in product.cols:
        c.tags.append('edit')

    return render_template('newproduct.html',
        form=Form,
        pnam=pnam,
        product=product)
