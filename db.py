import os, csv
import config

def dbpath(dbnam):
    return os.path.join(config.DB_ROOT, dbnam+'.csv')

def getdb(dbnam, cat=None):
    fd = open(dbpath(dbnam), "r")
    r = csv.reader(fd)
    return [row for row in r if not cat or row[0]==cat]

def putdb(dbnam, data):
    fd = open(dbpath(dbnam), "w")
    w = csv.writer(fd).writerows(data)