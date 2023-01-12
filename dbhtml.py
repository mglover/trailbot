class Form(object):
    row_idx = 0
    @classmethod
    def nextidx(cls):
        i = cls.row_idx
        cls.row_idx += 1
        return i

    @classmethod
    def cellname(cls, colnum):
        return "%i,%i" % (cls.row_idx, colnum)

    @classmethod
    def begin(cls, table, action="replace"):
        cls.row_idx=0
        r = []
        r.append('<form method="POST">')
        r.append('<input type="hidden" name="db" value="%s">'%table.dbnam)
        r.append('<input type="hidden" name="action" value="%s">'%action)
        return '\n'.join(r)

    @classmethod
    def end(cls):
        return "</form>"

    @classmethod
    def select(cls, row, idx):
        nam = cls.cellname(idx)
        val = row.data[idx]
        if 'options' in dir(val):
            h = '<select name="%s">' % nam
            for o in val.options():
                selected = str(o)==str(val) and 'selected' or ''
                h+= '\n\t<option value="%s" %s>%s</option>'%(o,selected,o)
            h += '</select>'
        return h

    @classmethod
    def _input(cls, row, idx, type="text"):
        nam=cls.cellname(idx)
        val=row.data[idx]
        return '<input type="%s" name="%s" value="%s">' % (type, nam,val)

    @classmethod
    def edit(cls, row, idx):
        nam = cls.cellname(idx)
        val = row.data[idx]
        if 'options' in dir(val):
             return cls.select(row, idx)
        else:
             return cls._input(row, idx)


    @classmethod
    def text(cls, row,idx):
            return str(row.data[idx])

    @classmethod
    def row_inputs(cls, row, cols):
        r = []
        for colnum in range(len(cols)):
            c = cols[colnum]
            if 'hidden' in c.tags:
                r.append(cls._input(row, colnum, type="hidden"))
            elif 'edit' in c.tags:
                r.append(cls.edit(row, colnum))
            elif 'computed' in c.tags:
                r.append(cls.text(row, colnum))
            else:
                r.append(cls._input(row, colnum, type="hidden") \
                    +cls.text(row,colnum))
        return r

    @classmethod
    def tr(cls, row,cols):
        cls.nextidx()
        r = []
        r.append("<tr>")
        cells = cls.row_inputs(row, cols)
        for c,v in zip(cols, cells):
            td = 'hidden' not in c.tags
            if td:
                htcls=str(c.typ.__name__)
                r.append('<td class="%s">'%htcls)
            r.append(v)
            if td:
                r.append("</td>")


        r.append("</tr>")
        return '\n'.join(r)

    @classmethod
    def thead(cls, cols):
        r = []
        r.append("<thead><tr>")
        for c in cols:
            if 'hidden' not in c.tags:
                htcls=str(c.typ.__name__)
                r.append('<th class="%s">%s</th>'%(htcls, c.name))
        r.append("</tr></thead>")
        return '\n'.join(r)

    @classmethod
    def tfoot(cls, row, cols):
        r = []
        r.append('<tfoot>')
        cells = zip(cols, row)
        for c,d in cells:
            htcls = str(c.typ.__name__)
            r.append('<td class="%s">%s</td>'%(htcls, d))
        r.append('</tfoot>')
        return '\n'.join(r)

    @classmethod
    def table(cls, rows, cols, footer=None):
        r = []
        r.append('<table class="db">')
        r.append(cls.thead(cols))
        for row in rows:
            r.append(cls.tr(row, cols))
        if footer:
            r.append(cls.tfoot(footer, cols))
        r.append("</table>")
        return '\n'.join(r)

    @classmethod
    def submit(cls, label):
        return '<input type=submit value="%s">'%label
