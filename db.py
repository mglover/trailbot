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
        self.tags = [t for t in tags.split(' ') if len(t)]

    def un(self, val):
        if val in self.tags:
            self.tags.remove(val)

class Table(object):
    dbnam = None
    cols = []

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

    @classmethod
    def getkey(cls, row):
        k =  [row[i] for i in range(len(cls.cols))
            if 'key' in cls.cols[i].tags]
        return tuple(k)

    @classmethod
    def keys(cls):
        return [key(row) for row in self.rows]

    @classmethod
    def indexFromKey(cls, key):
        for idx in range(len(cls.rows)):
            r = cls.rows[idx]
            if cls.getkey(r) == key:
                return idx
        raise ValueError("No %s: %s" % (cls.dbnam, keys))

    @classmethod
    def fromIndex(cls, idx):
        self = cls()
        self.idx = idx
        self.data = self.rows[idx];
        self.key = self.getkey(self.data)
        return self

    @classmethod
    def select(cls):
        return [cls.fromIndex(idx) for idx in range(len(cls.rows))]

    @classmethod
    def newrow(cls):
        self = cls()
        self.idx=0
        self.data=['' for c in cls.cols]
        self.key=None
        return self

    def __init__(self, *key):
        if key:
            self.key = key
            self.idx = self.indexFromKey(key)
            self.data = self.rows[self.idx]


class Component(Table):
    dbnam = 'components'
    cols = [
        Column('Component', str, 'key'),
        Column('Price', usd, 'edit')
    ]
    rows = []

    @classmethod
    def options(cls):
        return [r[0] for r in cls.rows]

    def price(self):
        return self.data[1]

    def __str__(self):
        return str(self.data[0])


class Product(Table):
    dbnam = 'assemblies'
    cols = [
        Column('Product', str, 'hidden key'),
        Column('Component', Component, 'key'),
        Column('Count',int, 'edit'),
    ]


tables = [Component, Product]
