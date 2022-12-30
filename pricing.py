from flask import request, redirect, render_template,url_for
from db import Column, Components, Products, usd

def updateFromPostData(postdata):
    return

def groupByColumn(colidx, rows):
    groups = {}
    for row in rows:
        key = row[colidx]
        if key not in groups: groups[key] = []
        groups[key].append(row)
    return groups


class Pricing(object):
    dbnam = Products.dbnam
    cols = Products.cols + [
        Column('Price Each', usd, 'computed'),
        Column('Subtotal', usd, 'computed')
    ]
    def __init__(self, rows):
        self.rows = []
        for pnam,cnam,cnt in rows:
            ea = Components.price(cnam)
            subt = ea * cnt
            self.rows.append((pnam,cnam,cnt,usd(ea),usd(subt)))

    def groupByProduct(self):
        col = Products.colidx("Product")
        return groupByColumn(col, self.rows)

    def total(self, rows):
        return sum([x[4] for x in rows])


def index():
    Components.load()
    Products.load()

    if request.method == 'POST':
        updateFromPostData(request.form)

    pricing = Pricing(Products.rows)

    return render_template('pricing.html',
        components=Components, pricing=pricing)
