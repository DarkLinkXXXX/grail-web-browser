"""HTML 3.0 <TABLE> tag support.

"""
# $Source: /home/john/Code/grail/src/html/table.py,v $
__version__ = '$Id: table.py,v 2.24 1996/04/09 21:40:49 bwarsaw Exp $'


import string
import regex
import grailutil
from Tkinter import *
from formatter import AbstractWriter, AbstractFormatter
from Viewer import Viewer
from types import *

FIXEDLAYOUT = 1
AUTOLAYOUT = 2
OCCUPIED = 101
EMPTY = 102

BadMojoError = 'Bad Mojo!  Infinite loop in cell height calculation.'



# ----- HTML tag parsing interface

class TableSubParser:
    def __init__(self):
	self._lasttable = None
	self._table_stack = []

    def start_table(self, parser, attrs):
	# create the table data structure
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
	    if not ti.lastbody:
		self.do_tr(parser, {})
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



def conv_stdunits(val):
    """Convert from string representation to Standard Units for Widths.

    pt -- points
    pi -- picas
    in -- inches
    cm -- centimeters
    mm -- millimeters
    em -- em units
    px -- screen pixels (the default)
    %  -- percentage
    *  -- CALS rel. widths

    Units representing, or pre-converted to screen pixels are
    converted to a floating point number.  All other units are
    represented as a tuple (num, repr).

    Note that only screen pixel and percentage units are currently
    handled by the table extension.

    """
    val = string.strip(val)
    if len(val) <= 0:
	return 0
    if val[-1] in ['%', '*']:
	return (grailutil.conv_float(val[:-1]), '%')
    if len(val) <= 1:
	return grailutil.conv_float(val)
    if val[-2:] in ['pt', 'pi', 'in', 'cm', 'mm', 'em']:
	return (grailutil.conv_float(val[:-2]), val[-2:])
    if val[-2:] == 'px':
	val = val[:-2]
    return grailutil.conv_float(val)


class AttrElem:
    """Base attributed table element.

    Common attrs    : id, class, style, lang, dir
    Alignment attrs : align, char, charoff, valign

    """

    def __init__(self, attrs):
	self.attrs = {}
	if type(attrs) == DictType:
	    attrs = attrs.items()
	# if its a dictionary, make a shallow copy, otherwise,
	# dictionary-ize the tuple passed in.
	for k, v in attrs:
	    self.attrs[string.lower(string.strip(k))] = v

    def attribute(self, attr, conv=None, default=None):
	if conv is None:
	    conv = grailutil.conv_integer
	return grailutil.extract_attribute(attr, self.attrs,
					   conv=conv,
					   default=default,
					   delete=None)


def _safe_mojo_height(cell):
    mojocnt = 0
    while mojocnt < 50:
	try:
	    return cell.height()
	except BadMojoError, mojoheight:
## 	    print 'Mojo sez:', mojoheight
	    cell.situate(height=2*mojoheight)
	    mojocnt = mojocnt + 1
    else:
	print 'Not even Mojo knows!  Mojo using:', mojoheight
	return mojoheight


class Table(AttrElem):
    """Top level table information object.

    Attrs: width, cols, border, frame, rules, cellspacing, cellpadding.

    """
    def __init__(self, parentviewer, attrs):
	AttrElem.__init__(self, attrs)
	self.parentviewer = parentviewer
	# attributes
	def conv_align(val):
	    return grailutil.conv_enumeration(
		grailutil.conv_normstring(val),
		['left', 'center', 'right'])
	self.Aalign = self.attribute('align', conv=conv_align, default='left')
	self.Awidth = self.attribute('width', conv=conv_stdunits)
	self.Acols = self.attribute('cols', conv=grailutil.conv_integer)
	if self.Acols:
	    self.layout = FIXEDLAYOUT
	else:
	    self.layout = AUTOLAYOUT
	# grok through the myriad of border/frame combinations.  this
	# is truly grotesque!
	def conv_frame(val):
	    return grailutil.conv_enumeration(
		grailutil.conv_normstring(val),
		['void', 'above', 'below', 'hsides', 'lhs', 'rhs',
		 'vsides', 'box', 'border'])
	Aframe = self.attribute('frame', conv=conv_frame)
	Aborder = self.attribute('border', conv=grailutil.conv_integer)
	if Aborder is None:
	    Aborder = self.attribute('border', conv=grailutil.conv_exists)
	    if Aborder:
		Aborder = 2
	    else:
		Aborder = 0
	# Tk can only handle frames or no frames, it can't do
	# individual or combinations of sides.
	if Aframe is None:
	    if Aborder is None:
		Aframe = 'void'
		borderwidth = 0
		relief = FLAT
	    elif Aborder > 0:
		Aframe = 'border'
		borderwidth = Aborder
		relief = RAISED
	    else:			# Aborder == 0
		Aframe = 'void'
		borderwidth = 0
		relief = FLAT
	elif Aframe == 'void':
	    borderwidth = 0
	    relief = FLAT
	else:
	    if Aborder is None:
		borderwidth = 2
	    else:
		borderwidth = Aborder
	    relief = RAISED
	self.Aframe = Aframe
	self.Aborder = Aborder
	# now do rules attribute
	def conv_rules(val):
	    return grailutil.conv_enumeration(
		grailutil.conv_normstring(val),
		['none', 'groups', 'rows', 'cols', 'all'])
	self.Arules = self.attribute('rules', conv=conv_rules)
	if self.Arules is None:
	    if Aborder == 0:
		self.Arules = 'none'
	    else:
		self.Arules = 'all'
	# cell spacing and padding
	self.Acellspacing = self.attribute('cellspacing',
					   conv=conv_stdunits,
					   default=2)
	self.Acellpadding = self.attribute('cellpadding',
					   conv=conv_stdunits,
					   default=0)
	# geometry
 	self.container = Canvas(parentviewer.text,
				relief=relief,
				borderwidth=borderwidth,
				highlightthickness=0,
				background=parentviewer.text['background'])

	self.caption = None
	self.cols = []			# multiple COL or COLGROUP
	self.colgroups = []
	self.thead = None
	self.tfoot = None
	self.tbodies = []
	self.lastbody = None
	self.lastcell = None
	self._mapped = None
	self._mappos = END
	# register with the parent viewer
	self.parentviewer.register_reset_interest(self._reset)
	self.parentviewer.register_resize_interest(self._resize)

    def _map(self):
	if not self._mapped:
	    self.container.pack()
	    self.parentviewer.add_subwindow(self.container,
					    index=self._mappos)
	    self._mapped = 1
	
    def finish(self):
	if self.layout == AUTOLAYOUT:
	    self._mappos = self.parentviewer.text.index(END)
	    self.parentviewer.text.insert(END, '\n\n')
	    self._autolayout_1()
	    self._autolayout_2()
	    self._autolayout_3()
	    if len(self.parentviewer.context.readers) <= 1:
		# if there are more readers than the one currently
		# loading the page with the table, defer mapping the
		# table
		self._map()
	    self.parentviewer.context.register_notification(self._notify)
	else:
	    print 'fixed layout for tables not yet supported!'

    def _autolayout_1(self):
	# internal representation of the table as a sparse array
	self._table = table = {}
	bodies = (self.thead or []) + self.tbodies + (self.tfoot or [])
	bw = self._borderwidth = grailutil.conv_integer(
	    self.container['borderwidth'])

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

## 	print '# of rows=', rowcount, '# of cols=', colcount

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
			# adjust the cell's colspan and rowspan
			# attributes so they aren't larger than the
			# table itself.
			cell.rowspan = min(cell.rowspan, rowcount-row)
			cell.colspan = min(cell.colspan, colcount-col)
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
	# save these for the next phase of autolayout
	self._colcount = colcount
	self._rowcount = rowcount

    def _autolayout_2(self):
	table = self._table
	colcount = self._colcount
	rowcount = self._rowcount
	bw = self._borderwidth

	# calculate column widths
	maxwidths = [0] * colcount
	minwidths = [0] * colcount
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
		maxwidth = cell.maxwidth() / cell.colspan
		minwidth = cell.minwidth() / cell.colspan
		for col_i in range(col, col + cell.colspan):
		    maxwidths[col_i] = max(maxwidths[col_i], maxwidth) + bw
		    minwidths[col_i] = max(minwidths[col_i], minwidth) + bw

	# save these for the next phase of autolayout
	self._maxwidths = maxwidths
	self._minwidths = minwidths

    def _autolayout_3(self):
	table = self._table
	colcount = self._colcount
	rowcount = self._rowcount
	bw = self._borderwidth
	maxwidths = self._maxwidths
	minwidths = self._minwidths

	mincanvaswidth = 2 * bw + self.Acellspacing * (colcount + 1)
	maxcanvaswidth = 2 * bw + self.Acellspacing * (colcount + 1)
	for col in range(colcount):
	    mincanvaswidth = mincanvaswidth + minwidths[col]
	    maxcanvaswidth = maxcanvaswidth + maxwidths[col]

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

	# calculate the available width that the table should render
	# itself in. first get the actual width, then apply any <TABLE
	# WIDTH=xxx> attributes.
	ptext = self.parentviewer.text
	viewerwidth = ptext.winfo_width() - \
		      2 * string.atof(ptext['padx']) - \
		      13		# TBD: kludge alert!
	if self.Awidth is None:
	    suggestedwidth = viewerwidth
	# units in screen pixels
	elif type(self.Awidth) in [IntType, FloatType]:
	    suggestedwidth = self.Awidth
	# other standard units
	elif type(self.Awidth) == TupleType:
	    if self.Awidth[1] == '%':
		suggestedwidth = viewerwidth * self.Awidth[0] / 100.0
	    # other standard units are not currently supported
	    else:
		suggestedwidth = veiwerwidth
	else:
	    print 'Tables internal inconsistency.  Awidth=', \
		  self.Awidth, type(self.Awidth)
	    suggestedwidth = viewerwidth
	
	# now we need to adjust for the available space (i.e. parent
	# viewer's width).  The Table spec outlines three cases...
	#
	# case 1: the min table width is equal to or wider than the
	# available space.  Assign min widths and let the user scroll
	# horizontally.
	if mincanvaswidth >= suggestedwidth:
	    cellwidths = minwidths
	# case 2: maximum table width fits within the available space.
	# set columns to their maximum width.
	elif maxcanvaswidth < suggestedwidth:
	    cellwidths = maxwidths
	# case 3: maximum width of the table is greater than the
	# available space, but the minimum table width is smaller.
	else:
	    W = suggestedwidth - mincanvaswidth
	    D = maxcanvaswidth - mincanvaswidth
	    adjustedwidths = [0] * colcount
	    for col in range(colcount):
		d = maxwidths[col] - minwidths[col]
		adjustedwidths[col] = minwidths[col] + d * W / D
	    cellwidths = adjustedwidths

	# calculate column heights.  this should be done *after*
	# cellwidth calculations, due to side-effects in the cell
	# algorithms
	cellheights = [0] * rowcount

	for row in range(rowcount):
	    for col in range(colcount):
		cell = table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    continue
		cellwidth = self.Acellspacing * (cell.colspan - 1)
		for w in cellwidths[col:col + cell.colspan]:
		    cellwidth = cellwidth + w
		cell.situate(width=cellwidth)
		cellheight = _safe_mojo_height(cell) / cell.rowspan
		for row_i in range(row, min(rowcount, row + cell.rowspan)):
		    cellheights[row_i] = max(cellheights[row_i], cellheight)

	canvaswidth = self.Acellspacing * (colcount - 1)
	for col in range(colcount):
	    canvaswidth = canvaswidth + cellwidths[col]

	ypos = bw + self.Acellspacing

	# if caption aligns top, then insert it now.  it doesn't need
	# to be moved, just resized
	if self.caption and self.caption.align <> 'bottom':
	    # must widen before calculating height!
	    self.caption.situate(width=canvaswidth)
	    height = self.caption.height()
	    self.caption.situate(x=bw, y=ypos, height=height)
	    ypos = ypos + height + self.Acellspacing

	# now place and size each cell
	for row in range(rowcount):
	    xpos = bw + self.Acellspacing
	    tallest = 0
	    for col in range(colcount):
		cell = table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    xpos = xpos + cellwidths[col] + self.Acellspacing
		    continue
		rowspan = min(rowcount, row + cell.rowspan)
		cellheight = self.Acellspacing * (rowspan - row - 1)
		for h in cellheights[row:min(rowcount, row + cell.rowspan)]:
		    cellheight = cellheight + h
		cell.situate(x=xpos, y=ypos, height=cellheight)
		xpos = xpos + cellwidths[col] + self.Acellspacing
	    ypos = ypos + cellheights[row] + self.Acellspacing

	# if caption aligns bottom, then insert it now.  it needs to
	# be resized and moved to the proper location.
	if self.caption and self.caption.align == 'bottom':
	    # must widen before calculating height!
	    self.caption.situate(width=canvaswidth)
	    height = self.caption.height()
	    self.caption.situate(x=bw, y=ypos, height=height)
	    ypos = ypos + height + self.Acellspacing

	self.container.config(width=canvaswidth + 2 * self.Acellspacing,
			      height=ypos-bw)

    def _reset(self, viewer):
	# called when the viewer is cleared
## 	print '_reset:', viewer
	self.parentviewer.context.unregister_notification(self._notify)
	self.parentviewer.unregister_reset_interest(self._reset)
	self.parentviewer.unregister_resize_interest(self._resize)
	# TBD: garbage collect internal structures, but not windows!

    def _resize(self, viewer):
	# called when the outer browser is resized (typically by the user)
## 	print '_resize:', viewer
	self._autolayout_3()

    def _notify(self, context):
	# receives notification when all readers for the shared
	# context have finished.  this typically occurs when there are
	# images inside table cells.  it will also happen for every
	# table cell exactly once, but if there are no embedded
	# images, the actual resize will be inhibited.
	recalc_needed = None
	for row in range(self._rowcount):
	    for col in range(self._colcount):
		cell = self._table[(row, col)]
		if cell in [EMPTY, OCCUPIED]:
		    continue
		status = cell.recalc()
		recalc_needed = recalc_needed or status
	if recalc_needed:
	    self._autolayout_2()
	    self._autolayout_3()
	if not self._mapped:
	    self._map()
	    

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
    width_max = width_max + (2 * border_x)
    # get minimum width of cell: longest word
    tw['wrap'] = WORD
    contents = tw.get(1.0, END)
    longest_word = reduce(max, map(len, string.split(contents)), 0)
    tw['width'] = longest_word + 1
    width_min = tw.winfo_width() + (2 * border_x)
    return float(width_min), float(width_max)

def _get_height(tw):
    linecount = _get_linecount(tw)
    tw['height'] = linecount
    tw.update_idletasks()
    tw.see(1.0)
    x, border_y, w, other_h, b = tw.dlineinfo(1.0)
    loopcnt = 0
    while 1:
	tw.see(1.0)
	info = tw.dlineinfo('end - 1 c')
	if info:
	    x, y, w, h, b = info
	    if h >= b:
		break
	# TBD: loopcnt check is probably unnecessary, but I'm not yet
	# convinced this algorithm always works.
	loopcnt = loopcnt + 1
	if loopcnt > 25:
	    raise BadMojoError, tw.winfo_height()
	linecount = linecount + 1
	tw['height'] = linecount
	tw.update_idletasks()
    # TBD: this isn't quite right.  We want to add border_y, but
    # that's not correct for the lower border.  I think we can ask the
    # textwidget for it's internal border space, but we may need to
    # add in relief space too.  Close approximation for now...
    #
    # Add 2 for descenders
    return y+h+border_y + 2



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
	# for callback notification
	self._fw = self._viewer.frame
	self._tw = self._viewer.text
	self._tw.config(highlightthickness=0)
	self._width = 0
	self._embedheight = 0
	# embedded window geometry regex
	self._re = regex.compile('%sx%s\+%s\+%s' % (('\([0-9]+\)',) * 4))

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
	return max(self._embedheight, _get_height(self._tw))

    def recalc(self):
	# recalculate width and height upon notification of completion
	# of all context's readers (usually image readers)
	min_nonaligned = self._minwidth
	maxwidth = self._maxwidth
	embedheight = self._embedheight
	recalc_flag = None
	# take into account all embedded windows
	for sub in self._viewer.subwindows:
	    geom = sub.winfo_geometry()
	    if self._re.search(geom) >= 0:
		[w, h, x, y] = map(grailutil.conv_integer,
				   self._re.group(1, 2, 3, 4))
	    min_nonaligned = max(min_nonaligned, x+w)
	    maxwidth = max(maxwidth, x+w)
	    embedheight = max(embedheight, y+h)
	    recalc_flag = 1
	self._embedheight = embedheight
	self._minwidth = min_nonaligned
	self._maxwidth = maxwidth
	return recalc_flag

    def finish(self, padding=0):
	# TBD: if self.layout == AUTOLAYOUT???
	self._x = self._y = 0
	fw = self._fw
	tw = self._tw
	# set the padding before grabbing the width
	tw['padx'] = padding
	# TBD: according to the W3C table spec, minwidth should really
	# be max(min_left + min_right, min_nonaligned).  Also note
	# that minwidth is recalculated by minwidth() call
	self._minwidth, self._maxwidth = _get_widths(self._tw)
	# first approximation of height.  this is the best we can do
	# without forcing an update_idletasks() fireworks display
	tw['height'] = _get_linecount(tw) + 1
	# initially place the cell in the canvas at position (0,0),
	# with the maximum width and closest approximation height.
	# situate() will be called later with the final layout
	# parameters.
	self._tag = self._container.create_window(
	    0, 0,
	    window=fw, anchor=NW,
	    width=self._maxwidth,
	    height=fw['height'])

    def situate(self, x=0, y=0, width=None, height=None):
	# canvas.move() deals in relative positioning, but we want
	# absolute coordinates
	xdelta = x - self._x
	ydelta = y - self._y
	self._x = x
	self._y = y
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
	self._tw.config(relief=FLAT, borderwidth=0)
	def conv_align(val):
	    return grailutil.conv_enumeration(
		grailutil.conv_normstring(val),
		['top', 'bottom', 'left', 'right']) or 'top'
	self.align = self.attribute('align', conv=conv_align)

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
	# relief and borderwidth are defined as table tag attributes
	if table.Arules == 'none':
	    relief = FLAT
	# TBD: rules=rows and rules=cols not yet implemented (is it
	# even possible in Tk?  probably, but could be painful
	else:
	    if table.Aframe == 'void':
		relief = FLAT
	    else:
		relief = SUNKEN
	self._tw.config(relief=relief, borderwidth=1)
	self.layout = table.layout
	# dig out useful attributes
	self.cellpadding = table.attribute('cellpadding', 0)
	self.rowspan = self.attribute('rowspan', default=1)
	self.colspan = self.attribute('colspan', default=1)
	if self.cellpadding < 0:
	    self.cellpadding = 0
	if self.rowspan < 0:
	    self.rowspan = 1
	if self.colspan < 0:
	    self.colspan = 1

    def init_style(self):
	pass

    def __repr__(self):
##	return '<%s>' % id(self) + '"%s"' % self._tw.get(1.0, END)[:-1]
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
