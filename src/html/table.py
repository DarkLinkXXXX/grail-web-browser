"""HTML 3.0 <TABLE> tag support.

"""
# $Source: /home/john/Code/grail/src/html/table.py,v $
__version__ = '$Id: table.py,v 2.1 1996/03/22 21:34:49 bwarsaw Exp $'


import string
import regex
from Tkinter import *
from formatter import AbstractWriter, AbstractFormatter
from Viewer import Viewer

FIXEDLAYOUT = 1
AUTOLAYOUT = 2
OCCUPIED = 101
EMPTY = 102



# ----- HTML tag parsing interface

class TableSubParser:
    def __init__(self):
	self._lasttable = None
	self._table_stack = []
	# get preferences
	from __main__ import app
	self._enabled = app.prefs.GetInt('tables', 'enabled')
	print 'tables are', (self._enabled and '(kinda)' or 'not'), 'enabled'

    def start_table(self, parser, attrs):
	# create the table data structure
	if self._enabled:
	    self._lasttable = Table(parser.viewer, attrs)
	    self._table_stack.append(self._lasttable)

    def end_table(self, parser):
	ti = self._lasttable 
	if ti:
	    self._close_cell(parser)
	    del self._table_stack[-1]
	    ti.close()

    def start_caption(self, parser, attrs):
	ti = self._lasttable 
	if ti:
	    caption = ti.caption = Caption(ti, parser.viewer, attrs)
	    caption.viewer.unfreeze()
	    formatter = AbstractFormatter(caption.viewer)
	    parser.push_formatter(formatter)

    def end_caption(self, parser):
	ti = self._lasttable 
	if ti and ti.caption:
	    ti.caption.viewer.freeze()
	    parser.pop_formatter()

    def do_colgroup(self, parser, attrs):
	ti = self._lasttable 
	if ti:
	    colgroup = Colgroup(attrs)
	    ti.colgroups.append(colgroup)

    def do_col(self, parser, attrs):
	ti = self._lasttable 
	if ti:
	    col = Col(attrs)
	    if ti.colgroups:
		last_colgroup = ti.colgroups[-1]
		last_colgroup.append(col)
	    else:
		ti.cols.append(col)

    def _do_body(self, parser, attrs):
	ti = self._lasttable
	self._close_cell(parser)
	body = HeadFootBody(attrs)
	ti.lastbody = body
	return body

    def do_thead(self, parser, attrs):
	ti = self._lasttable 
	if ti: ti.head = self._do_body(parser)

    def do_tfoot(self, parser, attrs):
	ti = self._lasttable 
	if ti: ti.foot = self._do_body(parser)

    def do_tbody(self, parser, attrs):
	ti = self._lasttable 
	if ti: ti.bodies.append(self._do_body(parser))

    def do_tr(self, parser, attrs):
	ti = self._lasttable 
	if ti:
	    tr = TR(attrs)
	    if not ti.lastbody:
		# this row goes into an implied tbody
		ti.lastbody = HeadFootBody()
		ti.tbodies.append(ti.lastbody)
	    ti.lastbody.trows.append(tr)

    def _do_cell(self, parser, attrs):
	ti = self._lasttable 
	if ti:
	    # close any previously opened cell
	    self._close_cell(parser)
	    # create a new formatter for the cell, made from a new subviewer
	    cell = ti.lastcell = Cell(ti, parser.viewer, attrs)
	    cell.viewer.unfreeze()
	    cell.viewer.text['wrap'] = NONE
	    formatter = AbstractFormatter(cell.viewer)
	    parser.push_formatter(formatter)
	    # create a new object to hold the attributes
	    rows = ti.lastbody.trows
	    if rows:
		rows[-1].cells.append(cell)

    def _close_cell(self, parser):
	# implicit close of an open table cell
	ti = self._lasttable
	if ti.lastcell:
	    ti.lastcell.viewer.freeze()
	    ti.lastcell.close()
	    ti.lastcell = None
	    parser.pop_formatter()

    def do_th(self, parser, attrs): self._do_cell(parser, attrs)
    def do_td(self, parser, attrs): self._do_cell(parser, attrs)



class AttrElem:
    """Base attributed table element.

    Common attrs    : id, class, style, lang, dir
    Alignment attrs : align, char, charoff, valign

    """

    def __init__(self, attrs):
	# I believe it's safe to `dictionary-ize' the elements in this
	# list by untupling.
	self.attrs = {}
	for k, v in attrs:
	    self.attrs[k] = v

    def attribute(self, attr):
	if self.attrs.has_key(attr):
	    return self.attrs[attr]
	else:
	    return None



def _get_real_size(textwidget):
    textwidget.see(1.0)
    # TBD: this sucks, since the user will see all the gross resizing
    # going on.  I really wish there was a way to hide this from
    # happening, but without the update_idletasks(), dlineinfo() won't
    # work.
    textwidget.update_idletasks()
    x, y, w, h, baseline = textwidget.dlineinfo('end - 1 c')
    return 2*x + w, 2*y + h

def _get_longest_line(textwidget, wrap=NONE):
    textwidget['wrap'] = wrap
    # TBD: another gross hack.  See above...
    textwidget.update_idletasks()
    longest = 0
    linecnt = string.atoi(string.splitfields(textwidget.index(END), '.')[0])
    for lineno in range(1, linecnt):
	index = '%d.0' % lineno
	textwidget.see(index)
	x, y, w, h, baseline = textwidget.dlineinfo(index)
	longest = max(longest, w)
    return longest

def _get_longest_word(textwidget):
    contents = textwidget.get(1.0, END)
    longest = reduce(max, map(len, string.split(contents)), 0)
    textwidget['width'] = longest + 1
    return _get_longest_line(textwidget, wrap=WORD)



class Table(AttrElem):
    """Top level table information object.

    Attrs: width, cols, border, frame, rules, cellspacing, cellpadding.

    """
    def __init__(self, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	self.parentviewer.text.insert(END, '\n')
## 	self.parentviewer.text.propagate(0)
	# public ivars
	self.layout = self.attribute('cols') and FIXEDLAYOUT or AUTOLAYOUT
	# geometry
	self.frame = Frame(parentviewer.text,
			   borderwidth=1,
			   relief=RAISED,
			   width=1000000, height=1000000)
	self.frame.pack()
	self.cellcontainer = Canvas(self.frame, relief=FLAT)
	self.cellcontainer.pack()
	self.caption = None
	self.cols = []			## multiple COL or COLGROUP
	self.colgroups = []
	self.thead = None
	self.tfoot = None
	self.tbodies = []
	self.lastbody = None
	self.lastcell = None

    def close(self):
	if self.layout == AUTOLAYOUT:
	    containerwidth = self._autolayout_1()
	    if self.caption:
		self.caption.situate(width=containerwidth)
	else:
	    pass
## 	self.parentviewer.text.propagate(1)

    def _autolayout_1(self):
	# internal representation of the table as a sparse array
	table = {}
	bodies = (self.thead or []) + self.tbodies + (self.tfoot or [])

	# calculate row and column counts
	colcount = 0
	rowcount = 0
	pending_rowspans = 0
	for tb in bodies:
	    for trow in tb.trows:
		pending_rowspans = max(0, pending_rowspans - 1)
		rowcolumns = len(trow.cells)
		rowspans = 0
		for cell in trow.cells:
		    if cell.colspan > 1:
			rowcolumns = rowcolumns + cell.colspan - 1
		    rowspans = max(rowspans, cell.rowspan)
		if rowspans > 1:
		    pending_rowspans = pending_rowspans + rowspans - 1
		rowcount = rowcount + 1
		colcount = max(colcount, rowcolumns)
	rowcount = rowcount + pending_rowspans

	print '# of rows=', rowcount, '# of cols=', colcount

	# populate an empty table
	for row in range(rowcount):
	    for col in range(colcount):
		table[(row, col)] = None

	# now populate the sparse array, watching out for multiple row
	# and column spanning cells, and for empty cells, which won't
	# get rendered.
	for tb in bodies:
	    row = 0
	    for trow in tb.trows:
		col = 0
		for cell in trow.cells:
		    if table[(row, col)] == OCCUPIED:
			col = col + 1
		    # the cell could be empty
		    if cell.is_empty():
			table[(row, col)] = EMPTY
		    else:
			table[(row, col)] = cell
		    # the cell could span multiple columns
		    cs = col + 1
		    for cs in range(cs, cs + cell.colspan - 1):
			for rs in range(row, row + cell.rowspan):
			    print 'occupying:', rs, cs
			    table[(rs, cs)] = OCCUPIED
		    col = cs
		row = row + 1

	# debugging
	print '==========', id(self)
	for row in range(rowcount):
	    print '[', 
	    for col in range(colcount):
		element = table[(row, col)]
		if element == EMPTY:
		    print 'EMPTY', 
		elif element == OCCUPIED:
		    print 'OCCUPIED',
		else:
		    print element,
	    print ']'
	print '==========', id(self)

	# calculate initial colspan=1 cell sizes
	cellwidths = [0] * colcount
	cellheights = [0] * rowcount
	for col in range(colcount):
	    for row in range(rowcount):
		cell = table[(row, col)]
		if cell not in [EMPTY, OCCUPIED]:
		    cellwidth = cell.width()
		    cellheight = cell.height()
		    cellwidths[col] = max(cellwidths[col], cellwidth)
		    cellheights[row] = max(cellheights[row], cellheight)

	canvaswidth = 0
	for width in cellwidths:
	    canvaswidth = canvaswidth + width

	# now place and size each cell
	ypos = 0
	for row in range(rowcount):
	    xpos = 0
	    tallest = 0
	    for col in range(colcount):
		cell = table[(row, col)]
		if cell == OCCUPIED:
		    continue
		if cell == EMPTY:
		    xpos = xpos + cellwidths[col]
		    continue
		cellwidth = 0
		cellheight = 0
		tallest = reduce(max, cellheights)
		for span in range(col, col + cell.colspan):
		    cellwidth = cellwidth + cellwidths[span]
		for span in range(row, row + cell.rowspan):
		    cellheight = cellheight + cellheights[span]
		cell.situate(self.cellcontainer,
			     x=xpos, y=ypos,
			     w=cellwidth, h=cellheight)
		xpos = xpos + cellwidth
	    ypos = ypos + tallest

	self.frame.propagate(1)
	self.parentviewer.add_subwindow(self.frame)
	self.cellcontainer.config(width=canvaswidth, height=ypos)
	self.parentviewer.text.insert(END, '\n')
	return canvaswidth
	    

##     def _do_autolayout(self):
## 	# go through each body part and figure out how many columns we
## 	# need.
## 	columncnt = 0
## 	rowcnt = 0
## 	bodies = (self.thead or []) + self.tbodies + (self.tfoot or [])
## 	for tb in bodies:
## 	    columncnt = max(columncnt, tb.get_column_count())
## 	for tb in bodies:
## 	    rowcnt = rowcnt + len(tb.trows)
## 	# create the table structure
## 	for row in range(rowcnt):
## 	    self.t.append([None] * columncnt)
## 	# gather cells into columns, while calculating mins/maxs
## 	colmins = [0] * columncnt
## 	colmaxs = [0] * columncnt
## 	row_i = 0
## 	for tb in bodies:
## 	    for row in tb.trows:
## 		col_i = 0
## 		for cell in row.cells:
## 		    # put cell in table
## 		    self.t[row_i][col_i] = cell
## 		    # calculate min and max
## 		    colmins[col_i] = max(colmins[col_i], cell.min_nonaligned)
## 		    colmaxs[col_i] = max(colmaxs[col_i], cell.maximum)
## 		    col_i = col_i + 1
## 		row_i = row_i + 1
## 	parentwidth = self.parentviewer.text['width']
## 	minwidth = 0
## 	for w in colmins:
## 	    minwidth = minwidth + w
## 	maxwidth = 0
## 	for w in colmaxs:
## 	    maxwidth = maxwidth + w
## 	# case 1, minimum table width is equal to or wider than the
## 	# available space.  assign minimum widths and allow the user
## 	# to scroll horizontally
## 	if minwidth >= parentwidth:
## 	    self._resize_to(colmins)
## 	# case 2, maximum table width fits in available space.  set
## 	# columns to max widths
## 	elif maxwidth < parentwidth:
## 	    self._resize_to(colmaxs)
## 	# case 3, max width of table is great than available space,
## 	# but min width is smaller.  spread difference out over cells.
## 	else:
## 	    pass

## 	# now place all the cells within the table's frame
## 	width=0
## 	y = 0
## 	for row in self.t:
## 	    x = 0
## 	    tallest = 0
## 	    for cell in row:
## 		if cell:
## 		    cell.move_to(x, y)
## 		    x = x + cell.width()
## 		    width = max(width, x)
## 		    tallest = max(tallest, cell.height())
## 	    y = y + tallest

## 	print self.t
## 	self.cellframe.place(width=width, height=y)

##     def _resize_to(self, colszs):
## 	for row in self.t:
## 	    for i in range(len(colszs)):
## 		size = colszs[i]
## 		if row[i]:
## 		    row[i].resize_to(size)



class Caption(AttrElem):
    """A table caption element."""
    def __init__(self, table, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	self.viewer = Viewer(master=table.frame,
			     scrolling=0,
			     stylesheet=parentviewer.stylesheet,
			     parent=parentviewer)
	self.viewer.frame.propagate(0)
	self.viewer.text['relief'] = FLAT
	align = string.lower(self.attribute('align') or '')
	if align <> 'bottom':
	    self.viewer.frame.pack(before=table.cellcontainer,
				   fill=NONE, expand=NO)
	else:
	    self.viewer.frame.pack(fill=NONE, expand=NO)

    def situate(self, width=None):
	if width <> None:
	    self.viewer.text.config(width=width, height=100000, wrap=WORD)
	    self.viewer.frame.config(width=width, height=100000)
	    self.viewer.text.tag_add('caption', 1.0, END)
	    self.viewer.text.tag_config('caption', justify=CENTER)
	w, h = _get_real_size(self.viewer.text)
	self.viewer.frame.config(width=w, height=h)
	    

class Colgroup(AttrElem):
    """A column group."""
    def __init__(self, attrs):
	AttrElem.__init__(self, attrs)
	self.cols = []

class Col(AttrElem):
    """A column."""

class HeadFootBody(AttrElem):
    """A generic THEAD, TFOOT, or TBODY."""

    def __init__(self, attrs=[]):
	AttrElem.__init__(self, attrs)
	self.trows = []

class TR(AttrElem):
    """A TR table row element."""

    def __init__(self, attrs):
	AttrElem.__init__(self, attrs)
	self.cells = []


class Cell(AttrElem):
    """A generic TH or TD table cell element."""

    def __init__(self, table, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.viewer = Viewer(master=table.frame,
			     scrolling=0,
			     stylesheet=parentviewer.stylesheet,
			     parent=parentviewer)
	self.viewer.text.config(relief=SUNKEN, borderwidth=1)
	self.viewer.text.pack(fill=BOTH, expand=YES)
	self.layout = table.layout
	self.maximum = 0
	self.min_nonaligned = 0
	self.min_left = 0
	self.min_right = 0
	self._width = 0
	self._height = 0
	# dig out useful attributes
	self.rowspan = string.atoi(self.attribute('rowspan') or '1')
	self.colspan = string.atoi(self.attribute('colspan') or '1')

    def __repr__(self):
	return '"%s"' % self.viewer.text.get(1.0, END)[:-1]

    def width(self): return self._width
    def height(self): return self._height
    def is_empty(self): return not self.viewer.text.get(1.0, 'end - 1 c')

    def close(self):
	if self.layout == AUTOLAYOUT:
	    # get the real true size of the widget
	    self._width, self._height = _get_real_size(self.viewer.text)
	    # find the maximum width of the cell, defined to be the
	    # width of the widest non-wrapped line
	    self.maximum = _get_longest_line(self.viewer.text)
	    # Now find the minimum width of the cell, defined to be
	    # the widest word or image, taking into account leading
	    # indents and list bullets.
	    #
	    # TBD: leading indents and list bullets aren't currently
	    # counted.  This method isn't perfect, but it should be
	    # fast and hopefully, accurate enough.
	    self.min_nonaligned = _get_longest_word(self.viewer.text)
	    # now take into account all embedded subwindows
	    for sw in self.viewer.subwindows:
		self.min_nonaligned = max(self.min_nonaligned, sw['width'])

    def situate(self, container, x, y, w, h):
	container.create_window(x, y,
				window=self.viewer.frame,
				anchor=NW,
				width=w, height=h)
	self._width = w
	self._height = h
	self._x = x
	self._y = y


if __name__ == '__main__':
    pass
else:
    tparser = TableSubParser()
    for attr in dir(TableSubParser):
	if attr[0] <> '_':
	    exec '%s = tparser.%s' % (attr, attr)
