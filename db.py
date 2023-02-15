import os, csv
import config
from flask import request

def rowsFromPostData(postdata):
    cells = []
    for k,v in postdata.items():
        try:
            r,c = k.split(',')
        except ValueError:
            continue
        cells.append((r,c,v))

    cells.sort()
    rows=[]
    last_r=cells[0][0]
    this_r = []
    for r,c,v in cells:
        if r != last_r:
            rows.append(this_r)
            this_r = []
            last_r = r
        this_r.append(v)
    rows.append(this_r)
    return rows

def dbpath(dbnam):
    return os.path.join(config.DB_ROOT, dbnam+'.csv')

def getdb(dbnam, cat=""):
    fd = open(dbpath(dbnam), "r")
    r = csv.reader(fd)
    return [row for row in r 
        if len(row) and (not cat or row[0]==cat)]

def putdb(dbnam, data):
    fd = open(dbpath(dbnam), 'w')
    w = csv.writer(fd)
    w.writerows(data)

class usd(float):
    def __init__(self, raw=0.0):
        float.__init__(raw)

    def __repr__(self):
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
    rows = []

    @classmethod
    def load(cls):
        cls.rows = [cls.parse(row) for row in getdb(cls.dbnam)]

    @classmethod
    def save(cls):
        fd = open(dbpath(cls.dbnam), "w")
        w = csv.writer(fd).writerows(
            [cls.unparse(row) for row in cls.rows])

    @classmethod
    def updateFromPostData(cls, postdata):
        postdata = dict([(k,v) for k,v in postdata.items()])
        dbnam = postdata['db']
        if dbnam != cls.dbnam:
            return
        postdata.pop('db')
        db = tables[dbnam]
        rows = rowsFromPostData(postdata)
        action = postdata.pop('action')
        if action == 'replace':
            cls.replace(rows)
        elif action == 'append':
            cls.append(rows)

    @classmethod
    def replace(cls, rows):
        cls.rows = [cls.parse(row) for row in rows]

    @classmethod
    def append(cls, rows):
        for row in rows: 
            cls.rows.append(cls.parse(row))

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
    def getkeyidxs(cls):
        return tuple([i for i in range(len(cls.cols)) 
            if 'key' in cls.cols[i].tags])

    @classmethod
    def getkey(cls, row=None):
        try:
            k = tuple([row[i] for i in cls.getkeyidxs()])
        except:
            raise ValueError(row, cls.getkeyidxs())
        return k

    @classmethod
    def keys(cls):
        return [key(row) for row in self.rows]

    @classmethod
    def indexFromKey(cls, key):
        for idx in range(len(cls.rows)):
            r = cls.rows[idx]
            k = cls.getkey(r)
            if k == key:
                return idx
        raise ValueError("No %s: #%s#" % (cls.dbnam, key), cls.rows)

    @classmethod
    def select(cls):
        return [cls(idx=idx) for idx in range(len(cls.rows))]

    def __init__(self, *key, idx=None, data=None):
        if data is None: data = {}
        if key:
            self.idx = self.indexFromKey(key)
            self.key = key
        elif idx is not None:
            self.idx = idx
            self.key = self.getkey(self.rows[idx])
        else:
            self.idx = None
            self.key = ()

        if self.idx is not None:
            self.data = self.rows[self.idx]
        elif key:
            self.data = self.rows[self.indexFromKey(key)]
        else:
            self.data = []
            for c in self.cols:
                d = data.get(c.name)
                if d: self.data.append(c.typ(d))
                else: self.data.append(c.typ())


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

    def __repr__(self):
        return str(self.data[0])


class Subassembly(Table):
    dbnam = 'subassembly'
    cols = [
        Column('Subassembly', str, 'hidden key'),
        Column('Component', Component, 'edit'),
        Column('Count', int, 'edit')
    ]

    @classmethod
    def enableComponents(cls):
        for cnam,ea in Component.rows:
            cls.append([(cnam,cnam,1),])

    @classmethod
    def disableComponents(cls):
        cls.rows = [r for r in cls.rows if str(r[0]) != str(r[1])]

    @classmethod
    def save(cls):
        pass

    @classmethod
    def options(cls):
        subs = [r[0] for r in cls.rows]
        uniq = list(set(subs))
        uniq.sort()
        return uniq

    def price(self):
        search,_,_ = self.data
        rows = list(filter(lambda r:r[0]==search, self.rows))
        return usd(sum([compo.price()*cnt for snam,compo,cnt in rows]))

    def __repr__(self):
        return self.data[0]

class Product(Table):
    dbnam = 'assemblies'
    cols = [
        Column('Product', str, 'hidden key'),
        Column('Subassembly', Subassembly, 'key'),
        Column('Count',int, 'edit'),
    ]


tables = {
    'components': Component, 
    'subassembly': Subassembly, 
    'assemblies':Product
}
