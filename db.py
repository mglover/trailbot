import os, csv
import config
from flask import request

def dbpath(dbnam):
    return os.path.join(config.DB_ROOT, dbnam+'.csv')

def getdb(dbnam, cat=""):
    fd = open(dbpath(dbnam), "r")
    r = csv.reader(fd)
    return [row for row in r 
        if len(row) and (not cat or row[0]==cat)]

class usd(float):
    def __init__(self, raw):
        float.__init__( raw)

    def __str__(self):
        return ("%.02f"%self)

class Column(object):
    def __init__(self, name, typ, tags):
        self.name = name
        self.typ = typ
        self.tags = tags

class Table(object):
    dbnam = None
    cols = []

    @classmethod
    def init(self, rows):
        cls.rows = rows

    @classmethod
    def load(cls):
        cls.rows = [cls.parse(row) for row in getdb(cls.dbnam)]

    @classmethod
    def save(cls):
        fd = open(dbpath(dbnam), "w")
        w = csv.writer(fd).writerows(
            [cls.unparse(row) for row in cls.rows])

    @classmethod
    def parse(cls,row):
        """ Type conversion from column defs"""
        return [c.typ(r) for c,r in zip(cls.cols, row)]

    @classmethod
    def unparse(cls, row):
        return row

    @classmethod
    def colidx(cls, name):
        for i in range(len(cls.cols)):
            if cls.cols[i].name == name:
                return i
        raise ValueError("No column %s" % name,)


class Components(Table):
    dbnam = 'components'
    cols = [
        Column('Component', str, 'key'),
        Column('Price', usd, 'edit')
    ]
    rows = []

    @classmethod
    def price(cls, nam):
        return dict(cls.rows)[nam]


class Products(Table):
    dbnam = 'assemblies'
    cols = [
        Column('Product', str, 'hidden key'),
        Column('Component', str, 'key'),
        Column('Count',int, 'edit'),
    ]


tables = [Components, Products]
