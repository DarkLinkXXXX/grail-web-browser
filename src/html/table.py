"""HTML 3.0 <TABLE> tag support.

"""
# $Source: /home/john/Code/grail/src/html/table.py,v $
__version__ = '$Id: table.py,v 2.5 1996/03/27 23:01:15 bwarsaw Exp $'


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
	    self._finish_cell(parser)
	    del self._table_stack[-1]
	    ti.finish()

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
	self._finish_cell(parser)
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

    def _do_cell(self, parser, attrs, header=None):
	ti = self._lasttable 
	if ti:
	    # finish any previously opened cell
	    self._finish_cell(parser)
	    # create a new formatter for the cell, made from a new subviewer
	    if header:
		cell = THCell(ti, parser, attrs)
	    else:
		cell = TDCell(ti, parser, attrs)
	    ti.lastcell = cell
	    cell.viewer.unfreeze()
	    cell.viewer.text['wrap'] = NONE
	    formatter = AbstractFormatter(cell.viewer)
	    parser.push_formatter(formatter)
	    cell.init_style()
	    # create a new object to hold the attributes
	    rows = ti.lastbody.trows
	    if rows:
		rows[-1].cells.append(cell)

    def _finish_cell(self, parser):
	# implicit finish of an open table cell
	ti = self._lasttable
	if ti.lastcell:
	    ti.lastcell.viewer.freeze()
	    ti.lastcell.finish()
	    ti.lastcell = None
	    parser.pop_formatter()

    def do_th(self, parser, attrs): self._do_cell(parser, attrs, 1)
    def do_td(self, parser, attrs): self._do_cell(parser, attrs)



def _get_linecount(tw):
    return string.atoi(string.splitfields(tw.index(END), '.')[0]) - 1

def _get_widths(tw):
    width_max = 0
    charwidth_max = 0
    border_x = None
    # get maximum width of cell: the longest line with no line wrapping
    tw['wrap'] = NONE
    border_x, y, w, h, b = tw.dlineinfo(1.0)
    linecnt = _get_linecount(tw) + 1
    for lineno in range(1, linecnt):
	index = '%d.0' % lineno
	tw.see(index)
	x, y, w, h, b = tw.dlineinfo(index)
	width_max = max(width_max, w)
	if lineno > 1:
	    charwidth = string.atoi(string.splitfields(
		tw.index('%s - 1 c' % index), '.')[1])
	    charwidth_max = max(charwidth_max, charwidth)
    width_max = width_max + (2 * border_x)
    # get minimum width of cell: longest word
    tw['wrap'] = WORD
    contents = tw.get(1.0, END)
    longest_word = reduce(max, map(len, string.split(contents)), 0) + 1
    tw['width'] = longest_word
    width_min = tw.winfo_reqwidth() + (2 * border_x)
    return charwidth_max, width_min, width_max

def _get_height(tw):
    linecount = _get_linecount(tw)
##     print tw.get(1.0, 'end - 1 c'), '[%d]:' % linecount,
##     print 'width=', tw['width'], tw.master['width'],
    tw['height'] = linecount
    tw.update_idletasks()
    tw.see(1.0)
    x, border_y, w, h, b = tw.dlineinfo(1.0)
    loopcnt = 0
    while 1:
## 	print 'loopcnt=', loopcnt,
	loopcnt = loopcnt + 1
	if loopcnt > 100:
	    raise 'Loop Badness Detected!'
	tw.see(1.0)
## 	print '<%s>' % tw.index('end - 1 c'),
	info = tw.dlineinfo('end - 1 c')
	if info:
## 	    print
	    break
	linecount = linecount + 1
## 	print 'linecount=', linecount
	tw['height'] = linecount
	tw.update_idletasks()
    x, y, w, h, b = info
    return border_y + y + h



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



class Table(AttrElem):
    """Top level table information object.

    Attrs: width, cols, border, frame, rules, cellspacing, cellpadding.

    """
    def __init__(self, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	self.parentviewer.text.insert(END, '\n')
	# public ivars
	self.layout = self.attribute('cols') and FIXEDLAYOUT or AUTOLAYOUT
	# geometry
	self.frame = Frame(parentviewer.text,
			   borderwidth=1,
			   relief=RAISED)
	self.frame.pack()
	self.cellcontainer = Canvas(self.frame, relief=FLAT)
	self.caption = None
	self.cols = []			## multiple COL or COLGROUP
	self.colgroups = []
	self.thead = None
	self.tfoot = None
	self.tbodies = []
	self.lastbody = None
	self.lastcell = None

    def finish(self):
	if self.layout == AUTOLAYOUT:
	    # TBD: temporary, should be add_subwindow() instead
	    self.cellcontainer.pack()
	    containerwidth = self._autolayout_1()
	    if self.caption:
		self.caption.finish()
	else:
	    pass

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
		table[(row, col)] = EMPTY

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
			cell.close()
		    else:
			table[(row, col)] = cell
		    # the cell could span multiple columns
		    cs = col + 1
		    for cs in range(cs, cs + cell.colspan - 1):
			for rs in range(row, row + cell.rowspan):
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
		if cell in [EMPTY, OCCUPIED]:
		    # empty cells don't contribute to the width of the
		    # column and occupied cells have already
		    # contributed to column widths
		    continue
		elif cell.colspan > 1:
		    # cells that span more than one column evenly
		    # apportion the min/max widths to each of the
		    # consituent columns (this is how Arena does it as
		    # per the latest Table HTML spec).
		    cellwidth = float(cell.width()) / cell.colspan
		    for col_i in range(col, col + cell.colspan):
			cellwidths[col_i] = max(cellwidths[col_i], cellwidth)
		else:
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
		cell.situate(x=xpos, y=ypos,
			     w=cellwidth, h=cellheight)
		xpos = xpos + cellwidth
	    ypos = ypos + tallest

	self.parentviewer.add_subwindow(self.frame)
	self.cellcontainer.config(width=canvaswidth, height=ypos)
	self.parentviewer.text.insert(END, '\n')
	return canvaswidth
	    

class Caption(AttrElem):
    """A table caption element."""
    def __init__(self, table, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	self.viewer = Viewer(master=table.frame,
			     scrolling=0,
			     stylesheet=parentviewer.stylesheet,
			     parent=parentviewer)
	self.viewer.text['relief'] = FLAT
	self._align = string.lower(self.attribute('align') or '')
	self._packmaster = table.cellcontainer

    def finish(self):
	fw, tw = self.viewer.frame, self.viewer.text
## 	print self._align
	if self._align == 'bottom':
	    fw.pack(after=self._packmaster, fill=BOTH, expand=YES)
	else:
	    fw.pack(before=self._packmaster, fill=BOTH, expand=YES)
	# get widths and heights.  note the width must be set before
	# the true height can be calculated.
	cmax, wmin, wmax = _get_widths(tw)
	fw['width'] = wmax
	h = _get_height(tw)
	fw['height'] = h
	# set the style of the contained text
	self.viewer.text.tag_add('contents', 1.0, END)
	self.viewer.text.tag_config('contents', justify=CENTER)
	

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

    def __init__(self, table, parser, attrs):
	AttrElem.__init__(self, attrs)
	self._parser = parser
	self._container = table.cellcontainer
	self._cellpadding = table.attribute('cellpadding')
	self.viewer = Viewer(master=table.cellcontainer,
			     scrolling=0,
			     stylesheet=parser.viewer.stylesheet,
			     parent=parser.viewer)
	self.viewer.text.config(relief=SUNKEN, borderwidth=1)
	self.viewer.text.pack(fill=BOTH, expand=YES)
	self.layout = table.layout
	self.maximum = 0
	self.min_nonaligned = 0
	self.min_left = 0
	self.min_right = 0
	self._width = 0
	self._height = None
	# dig out useful attributes
	self.rowspan = string.atoi(self.attribute('rowspan') or '1')
	self.colspan = string.atoi(self.attribute('colspan') or '1')

    def close(self): self.viewer.close()

    def init_style(self):
	pass

    def __repr__(self):
	return '"%s"' % self.viewer.text.get(1.0, END)[:-1]

    def width(self):
	return self._width

    def height(self):
	if self._height is None:
	    self._height = _get_height(self.viewer.text)
	return self._height

    def is_empty(self): return not self.viewer.text.get(1.0, 'end - 1 c')

    def finish(self):
	if self.layout == AUTOLAYOUT:
	    fw, tw = self.viewer.text, self.viewer.text
	    # set the cellpadding
	    padding = string.atoi(self._cellpadding or '')
	    tw['padx'] = padding
	    # get the cell's widths
	    cmax, self.min_nonaligned, self._width = _get_widths(tw)
	    fw.propagate(0)
	    fw['width'] = self._width
	    # now take into account all embedded subwindows
	    for sw in self.viewer.subwindows:
		self.min_nonaligned = max(self.min_nonaligned, sw['width'])
	    # Make a first pass attempt at getting the cell to the
	    # proper size.  This isn't perfect, but it's the best we
	    # can do without forcing an update_idletasks() and causing
	    # fireworks.  Later, situate() will be called to do the
	    # final sizing and positioning of the cell.
	    tw['height'] = _get_linecount(tw) + 1

    def situate(self, x, y, w, h):
	fw = self.viewer.frame
	fw.propagate(1)
	fw.config(width=w, height=h)
	self._container.create_window(x, y,
				      window=fw, anchor=NW,
				      width=w, height=h)
	self._width = w
	self._height = h
	self._x = x
	self._y = y

class TDCell(Cell):
    pass

class THCell(Cell):
    def init_style(self):
	# TBD: this should be extracted from stylesheets and/or preferences
	self._parser.get_formatter().push_font((None, None, 1, None))

    def finish(self):
	Cell.finish(self)
	self.viewer.text.tag_add('contents', 1.0, END)
	self.viewer.text.tag_config('contents', justify=CENTER)


if __name__ == '__main__':
    pass
else:
    tparser = TableSubParser()
    for attr in dir(TableSubParser):
	if attr[0] <> '_':
	    exec '%s = tparser.%s' % (attr, attr)
