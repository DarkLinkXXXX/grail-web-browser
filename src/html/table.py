"""HTML 3.0 <TABLE> tag support.

"""
# $Source: /home/john/Code/grail/src/html/table.py,v $
__version__ = '$Id: table.py,v 2.11 1996/04/01 17:42:14 bwarsaw Exp $'


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
	    caption.unfreeze()
	    parser.push_formatter(caption.new_formatter())

    def end_caption(self, parser):
	ti = self._lasttable 
	if ti and ti.caption:
	    ti.caption.freeze()
	    parser.pop_formatter()
	    ti.caption.finish()

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
	    cell.unfreeze()
	    parser.push_formatter(cell.new_formatter())
	    cell.init_style()
	    # create a new object to hold the attributes
	    rows = ti.lastbody.trows
	    if rows:
		rows[-1].cells.append(cell)

    def _finish_cell(self, parser):
	# implicit finish of an open table cell
	ti = self._lasttable
	if ti.lastcell:
	    ti.lastcell.freeze()
	    ti.lastcell.finish()
	    ti.lastcell = None
	    parser.pop_formatter()

    def do_th(self, parser, attrs): self._do_cell(parser, attrs, 1)
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



class Table(AttrElem):
    """Top level table information object.

    Attrs: width, cols, border, frame, rules, cellspacing, cellpadding.

    """
    def __init__(self, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	# public ivars
	self.layout = self.attribute('cols') and FIXEDLAYOUT or AUTOLAYOUT
	# geometry
	self.frame = Frame(parentviewer.text,
			   borderwidth=2,
			   relief=RAISED)
 	self.container = Canvas(self.frame, relief=FLAT)
	self.caption = None
	self.cols = []			# multiple COL or COLGROUP
	self.colgroups = []
	self.thead = None
	self.tfoot = None
	self.tbodies = []
	self.lastbody = None
	self.lastcell = None

    def finish(self):
	if self.layout == AUTOLAYOUT:
	    self.parentviewer.text.insert(END, '\n')
	    containerwidth = self._autolayout_1()
	    self.container.pack()
	    self.parentviewer.add_subwindow(self.frame)
	    self.parentviewer.text.insert(END, '\n')
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
## 	rowcount = rowcount + pending_rowspans

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
		    # the cell could span multiple columns. TBD: yick!
		    for cs in range(col+1, col + cell.colspan):
			table[(row, cs)] = OCCUPIED
			for rs in range(row+1, row + cell.rowspan):
			    table[(rs, cs)] = OCCUPIED
		    for rs in range(row+1, row + cell.rowspan):
			table[(rs, col)] = OCCUPIED
			for cs in range(col+1, col + cell.colspan):
			    table[(rs, cs)] = OCCUPIED
		    col = col + 1
		row = row + 1

	# debugging
## 	print '==========', id(self)
## 	for row in range(rowcount):
## 	    print '[', 
## 	    for col in range(colcount):
## 		element = table[(row, col)]
## 		if element == EMPTY:
## 		    print 'EMPTY', 
## 		elif element == OCCUPIED:
## 		    print 'OCCUPIED',
## 		else:
## 		    print element,
## 	    print ']'
## 	print '==========', id(self)

	# calculate column widths
	cellmaxwidths = [0] * colcount
	cellminwidths = [0] * colcount
	cellheights = [0] * rowcount
	for col in range(colcount):
	    for row in range(rowcount):
		cell = table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    # empty cells don't contribute to the width of the
		    # column and occupied cells have already
		    # contributed to column widths
		    continue
		# cells that span more than one column evenly
		# apportion the min/max widths to each of the
		# consituent columns (this is how Arena does it as per
		# the latest Table HTML spec).
		maxwidth = float(cell.maxwidth()) / cell.colspan
		minwidth = float(cell.minwidth()) / cell.colspan
		for col_i in range(col, col + cell.colspan):
		    cellmaxwidths[col_i] = max(cellmaxwidths[col_i], maxwidth)
		    cellminwidths[col_i] = max(cellminwidths[col_i], minwidth)

	mincanvaswidth = 0
	maxcanvaswidth = 0
	for col in range(colcount):
	    mincanvaswidth = mincanvaswidth + cellminwidths[col]
	    maxcanvaswidth = maxcanvaswidth + cellmaxwidths[col]

	# now we need to adjust for the available space (i.e. parent
	# viewer's width).  The Table spec outlines three cases...
	ptext = self.parentviewer.text
	viewerwidth = ptext.winfo_reqwidth() - \
		      2 * string.atof(ptext['padx']) - \
		      13		# TBD: kludge alert!
	print 'viewerwidth=', viewerwidth, 'mincanvaswidth=', mincanvaswidth, \
	      'maxcanvaswidth=', maxcanvaswidth
	# case 1: the min table width is equal to or wider than the
	# available space.  Assign min widths and let the user scroll
	# horizontally.
	if mincanvaswidth >= viewerwidth:
	    print 'using min widths:',
	    cellwidths = cellminwidths
	# case 2: maximum table width fits within the available space.
	# set columns to their maximum width.
	elif maxcanvaswidth < viewerwidth:
	    print 'using max widths:',
	    cellwidths = cellmaxwidths
	# case 3: maximum width of the table is greater than the
	# available space, but the minimum table width is smaller.
	else:
	    print 'using adjusted widths:',
	    W = viewerwidth - mincanvaswidth
	    D = maxcanvaswidth - mincanvaswidth
	    adjustedwidths = [0] * rowcount
	    for col in range(colcount):
		d = cellmaxwidths[col] - cellminwidths[col]
		adjustedwidths[col] = float(cellminwidths[col]) + d * W / D
	    cellwidths = adjustedwidths

	# calculate column heights.  this should be done *after*
	# cellwidth calculations, due to side-effects in the cell
	# algorithms
	for row in range(rowcount):
	    for col in range(colcount):
		cell = table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    continue
		cell.situate(width=cellwidths[col])
		cellheight = float(cell.height()) / cell.rowspan
		for row_i in range(row, min(rowcount, row + cell.rowspan)):
		    cellheights[row_i] = max(cellheights[row_i], cellheight)

	canvaswidth = 0
	for row in range(rowcount):
	    print cellwidths[row]
	    canvaswidth = canvaswidth + cellwidths[row]
	print 'canvaswidth=', canvaswidth

	ypos = 0

	# if caption aligns top, then insert it now.  it doesn't need
	# to be moved, just resized
	if self.caption and self.caption.align <> 'bottom':
	    height = self.caption.height()
	    self.caption.situate(width=canvaswidth, height=height)
	    ypos = ypos + height

	# now place and size each cell
	for row in range(rowcount):
	    xpos = 0
	    tallest = 0
	    for col in range(colcount):
		cell = table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    xpos = xpos + cellwidths[col]
		    continue
		cellwidth = 0
		cellheight = 0
		for span in range(col, col + cell.colspan):
		    cellwidth = cellwidth + cellwidths[span]
		for span in range(row, min(rowcount, row + cell.rowspan)):
		    cellheight = cellheight + cellheights[span]
		cell.situate(xdelta=xpos, ydelta=ypos,
			     width=cellwidth, height=cellheight)
		xpos = xpos + cellwidths[col]
	    ypos = ypos + cellheights[row]

	# if caption aligns bottom, then insert it now.  it needs to
	# be resized and moved to the proper location.
	if self.caption and self.caption.align == 'bottom':
	    height = self.caption.height()
	    self.caption.situate(ydelta=ypos,
				 width=canvaswidth,
				 height=height)
	    ypos = ypos + height

	self.container.config(width=canvaswidth, height=ypos)
	return canvaswidth
	    

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


def _get_linecount(tw):
    return string.atoi(string.splitfields(tw.index(END), '.')[0]) - 1

def _get_widths(tw):
    width_max = 0
##     charwidth_max = 0
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
## 	if lineno > 1:
## 	    charwidth = string.atoi(string.splitfields(
## 		tw.index('%s - 1 c' % index), '.')[1])
## 	    charwidth_max = max(charwidth_max, charwidth)
    width_max = width_max + (2 * border_x)
    # get minimum width of cell: longest word
    tw['wrap'] = WORD
    contents = tw.get(1.0, END)
    longest_word = reduce(max, map(len, string.split(contents)), 0) + 1
    tw['width'] = longest_word
    width_min = tw.winfo_reqwidth() + (2 * border_x)
##     return charwidth_max, width_min, width_max
    return width_min, width_max

def _get_height(tw):
    linecount = _get_linecount(tw)
    tw['height'] = linecount
    tw.update_idletasks()
    tw.see(1.0)
    x, border_y, w, h, b = tw.dlineinfo(1.0)
    loopcnt = 0
    while 1:
	# TBD: loopcnt check is probably unnecessary, but I'm not yet
	# convinced this algorithm always works.
	loopcnt = loopcnt + 1
	if loopcnt > 1000:
	    raise 'Loop Badness Detected!'
	tw.see(1.0)
	info = tw.dlineinfo('end - 1 c')
	if info:
	    break
	linecount = linecount + 1
	tw['height'] = linecount
	tw.update_idletasks()
    x, y, w, h, b = info
    # TBD: this isn't quite right.  We want to add border_y, but
    # that's not correct for the lower border.  I think we can ask the
    # textwidget for it's internal border space, but we may need to
    # add in relief space too.  Close approximation for now...
    return (2 * border_y) + y + h



class ContainedText(AttrElem):
    """Base class for a text widget contained as a cell in a canvas.
    Both Captions and Cells are derived from this class.

    """
    def __init__(self, table, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self._table = table
	self._container = table.container
	self._viewer = Viewer(master=table.container,
			      context=parentviewer.context,
			      scrolling=0,
			      stylesheet=parentviewer.stylesheet,
			      parent=parentviewer)
	self._fw = self._viewer.frame
	self._tw = self._viewer.text
	self._width = 0
	self._height = None		# if None do expensive calculation

    def new_formatter(self):
	return AbstractFormatter(self._viewer)

    def freeze(self): self._viewer.freeze()
    def unfreeze(self): self._viewer.unfreeze()
    def close(self): self._viewer.close()

    def maxwidth(self):
	return self._maxwidth		# not useful until after finish()
    def minwidth(self):
	return self._minwidth		# likewise

    def height(self):
	if self._height is None:
	    self._height = _get_height(self._tw)
	return self._height

    def finish(self, padding=0):
	# TBD: if self.layout == AUTOLAYOUT???
	fw = self._fw
	tw = self._tw
	# set the padding before grabbing the width
	tw['padx'] = padding
	min_nonaligned, self._maxwidth = _get_widths(tw)
	# first approximation of height.  this is the best we can do
	# without forcing an update_idletasks() fireworks display
	tw['height'] = _get_linecount(tw) + 1
	# take into account all embedded windows
	for sub in self._viewer.subwindows:
	    min_nonaligned = max(min_nonaligned, sw['width'])
	# initially place the cell in the canvas at position (0,0),
	# with the maximum width and closest approximation height.
	# situate() will be called later with the final layout
	# parameters.
	self._tag = self._container.create_window(
	    0, 0,
	    window=fw, anchor=NW,
	    width=self._maxwidth,
	    height=fw['height'])
	# TBD: according to the W3C table spec, minwidth should really
	# be max(min_left + min_right, min_nonaligned)
	self._minwidth = min_nonaligned

    def situate(self, xdelta=0, ydelta=0, width=None, height=None):
	self._container.move(self._tag, xdelta, ydelta)
	if width <> None and height <> None:
	    self._container.itemconfigure(self._tag,
					  width=width, height=height)
	elif width <> None:
	    self._container.itemconfigure(self._tag, width=width)
	else:
	    self._container.itemconfigure(self._tag, height=height)



class Caption(ContainedText):
    """A table caption element."""
    def __init__(self, table, parentviewer, attrs):
	ContainedText.__init__(self, table, parentviewer, attrs)
	self._tw['relief'] = FLAT
	self.align = string.lower(self.attribute('align') or '')

    def finish(self, padding=0):
	ContainedText.finish(self, padding=0)
	# set the style of the contained text
	self._viewer.text.tag_add('contents', 1.0, END)
	self._viewer.text.tag_config('contents', justify=CENTER)


class Cell(ContainedText):
    """A generic TH or TD table cell element."""

    def __init__(self, table, parser, attrs):
	ContainedText.__init__(self, table, parser.viewer, attrs)
	self._parser = parser
	self._tw.config(relief=SUNKEN, borderwidth=2)
	self.layout = table.layout
	# dig out useful attributes
	self.cellpadding = string.atoi(table.attribute('cellpadding') or '')
	self.rowspan = string.atoi(self.attribute('rowspan') or '1')
	self.colspan = string.atoi(self.attribute('colspan') or '1')
	if self.rowspan < 0:
	    self.rowspan = 1
	if self.colspan < 0:
	    self.colspan = 1

    def init_style(self):
	pass

    def __repr__(self):
	return '"%s"' % self._tw.get(1.0, END)[:-1]

    def is_empty(self):
	return not self._tw.get(1.0, 'end - 1 c')

    def finish(self, padding=0):
	ContainedText.finish(self, padding=self.cellpadding)


class TDCell(Cell):
    pass

class THCell(Cell):
    def init_style(self):
	# TBD: this should be extracted from stylesheets and/or preferences
	self._parser.get_formatter().push_font((None, None, 1, None))

    def finish(self):
	Cell.finish(self)
	self._tw.tag_add('contents', 1.0, END)
	self._tw.tag_config('contents', justify=CENTER)


if __name__ == '__main__':
    pass
else:
    tparser = TableSubParser()
    for attr in dir(TableSubParser):
	if attr[0] <> '_':
	    exec '%s = tparser.%s' % (attr, attr)
