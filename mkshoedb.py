#!/usr/bin/python
import csv, os
from db import getdb, putdb

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

hiker=welt+vegtan+ankle+derby+cork+heel

products =[
    ('#welted', mkprice(hiker), 'Welted derby ankle boot', 'before.jpg'),
    ('#turn', mkprice(turn), 'Low-cut Carolingian', 'turnshoes_jpg.jpg'),
    ('#turn', mkprice(turn+ankle), 'Carolingian ankle boot', 'trailshoe.jpg'),
    ('#turn', mkprice(turn+derby), 'Low-cut derby', 'turnshoes_liz.jpg'),
    ]


db = putdb('shoes', products)

