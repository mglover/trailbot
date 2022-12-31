from flask import request, redirect, render_template,url_for
from db import Column, Component, Product, usd

def updateFromPostData(postdata):
    return


def html_select(row, idx):
    nam = "%i,%i"%(row.idx,idx)
    val = row.data[idx]
    if 'options' in dir(row.data[idx]):
        h = '<select name="%s">' % nam
        for v in val.options():
            selected = v==val and 'selected' or ''
            h+= '\n\t<option value="%s" %s>%s</option>'%(v,selected,v)
        h += '</select>'
    return h

def html_input(row, idx, type="text"):
    nam="%i,%i"%(row.idx,idx)
    val=row.data[idx]
    return '<input type="%s" name="%s" value="%s">' % (type, nam,val)

def html_edit(row, idx, **kwargs):
    nam = "%i,%i"%(row.idx,idx)
    val = row.data[idx]
    if 'options' in dir(row.data[idx]):
         return html_select(row, idx)
    else:
         return html_input(row, idx)

def html_hidden(row, idx):
    return  html_input(row, idx, type="hidden")

def html_text(row,idx):
        return str(row.data[idx])


class View(object):
    vcols = []
    def __init__(self, table, rows=None):
        self.table = table
#        print([c.name for c in self.table.cols+self.vcols])
        self.cols = self.table.cols + self.vcols
        self.rows = rows or []
#        for r in self.rows:
#            print(r.data)
    @classmethod
    def fromTable(cls, table):
        rows = [cls.compute(r) for r in table.select()]
        return cls(table, rows)

    @classmethod
    def compute(cls, row):
        return row

    def append(self, row):
        self.rows.append(self.compute(row))

    def forminputs(self, row):
        r = []
        for colnum in range(len(self.cols)):
            c = self.cols[colnum]
            if 'hidden' in c.tags:
                r.append(html_hidden(row, colnum))
            elif 'edit' in c.tags:
                print('EDIT', row, colnum)
                r.append(html_edit(row, colnum))
            elif 'computed' in c.tags:
                print('COMPUTED', row, colnum)
                r.append(html_text(row, colnum))
            else:
                print('DEFAULT', row, colnum)
                r.append(html_hidden(row, colnum)+
                    html_text(row,colnum))
        return r

    def tHeader(self):
        r = []
        r.append("<tr>")
        for c in self.cols:
            if 'hidden' not in c.tags:
                r.append("<td>"+c.name+"</td>")
        r.append("</tr>")
        return '\n'.join(r)

    def formTable(self):
        r = []
        r.append('<table class="db">')
        r.append(self.tHeader())
        for row in self.rows:
            r.append("<tr>")
            cells = self.forminputs(row)
            for c,v in zip(self.cols, cells):
                if 'hidden' not in c.tags:
                    r.append("<td>"+v+"</td>")
            r.append("</tr>")
        r.append("</table>")
        return '\n'.join(r)

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
        subt = ea * cnt
        row.data = (pnam,compo,cnt,ea,subt)
        return row

    def total(self):
        return sum([x.data[4] for x in self.rows])


def index():
    Component.load()
    Product.load()

    if request.method == 'POST':
        updateFromPostData(request.form)

    return render_template('pricing.html',
        components=View.fromTable(Component), 
        pricing=PricingView.fromTable(Product))


def new():
    Component.load()
    Product.load()

    product = View(Product, [Product.newrow()])
    return render_template('newproduct.html',
        product=product)
