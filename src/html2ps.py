"""HTML to PostScript translator.

This module uses the AbstractWriter class interface defined by Grail
to generate PostScript corresponding to a stream of HTML text.  The
HTMLParser class scans the HTML stream, generating high-level calls to
an AbstractWriter object.  This module defines a class derived from
AbstractWriter, called PSWriter, that supports this high level
interface as appropriate for PostScript generation.
"""

import sys
import string
import StringIO
import regsub
from formatter import *



# debugging
RECT_DEBUG = 0
DEBUG = 0

def _debug(text):
    if DEBUG:
	sys.stderr.write(text)
	sys.stderr.flush()


# Font definitions and metrics.

# This dictionary maps PostScript font names to the normal, bold and
# italic suffixes for the font.  Key is the short name describing the
# font, value is a tuple indicating the real name of the font (for
# mapping fonts to other fonts), then the regular, bold, and italic
# suffix modifiers of the font.  Note that if their is no regular name
# modifier, then use the empty string, but if there is a regular name
# modifier, make sure it includes a leading dash.  Other modifiers
# should not include the dash.

fonts = {
    'Times':            (None, '-Roman', 'Bold', 'Italic'),
    'Helvetica':        (None, '',       'Bold', 'Oblique'),
    'NewCenturySchlbk': (None, '-Roman', 'Bold', 'Italic'),
    'Courier':          (None, '',       'Bold', 'Oblique'),
    # The code from HTML-PSformat.c says:
    # "This is a nasty trick, I have put Times in place of Lucida,
    # because most printers don't have Lucida font"
    # Hmm...  -BAW
    #'Lucida':           ('Times', None, 'Bold', 'Italic'),
    'Lucida':           (None, '', 'Bold', 'Italic'),
    }

# The font family to font metrics dictionaries.  Each dictionary
# contains a mapping between characters in the 0-256 range and their
# widths in points.  It is assumed that different font sizes scale
# these widths linearly, but this is not actually the case.  Close
# enough for jazz.
#
# Oh, and yes I hand calculated these based on my printer's output.
# It's certainly possible I got some of these wrong, and in fact I'm
# seeing about a 10% deviation in calculated size to actual size (the
# latter coming up 10% less that the former).  Don't know why that is
# exactly, but I suspect it's some incorrect values in the numbers
# below.

font_metrics = {}

# 12 point, fixed width font metrics, all chars are the same width.
# for speed, I'll actually implement this differently
font_metrics['Courier'] = 7.2

# Standard variable width font is Helvetica
helv_charmap = {}
def fill_hfm(psz, chars):
    for c in chars: helv_charmap[c]=psz

fill_hfm(0.0, range(31))
fill_hfm(0.0, range(128,256))
fill_hfm(2.6642, "'`ijl")
fill_hfm(3.1202, '|')
fill_hfm(3.3362, ' !:;[],./Ift\\')
fill_hfm(3.9962, '()r')
fill_hfm(4.0083, '{}')
fill_hfm(4.2602, '"')
fill_hfm(4.6683, '*')
fill_hfm(5.6283, '^')
fill_hfm(6.0004, 'Jcksvxyz')
fill_hfm(6.6724, '#$0123456789?L_abdeghnopqu')
fill_hfm(7.0084, '+-<=>~')
fill_hfm(7.3324, 'FTZ')
fill_hfm(8.0045, '&ABEKPSVXY')
fill_hfm(8.6645, 'CDHNRUw')
fill_hfm(9.3366, 'GOQ')
fill_hfm(9.9966, 'Mm')
fill_hfm(10.6687, '%')
fill_hfm(11.3287, 'W')
fill_hfm(12.1807, '@')

# sanity check
#for c in range(32, 127):
#    width = helv_charmap[chr(c)]
#    if width is None or width <= 0:
#	raise KeyError, c
font_metrics['Helvetica'] = helv_charmap

# Some of the Helvetica Bold characters are a bit wider than their
# normal versions.  However there seems to be no difference in metrics
# imposed by the italics modifier

helv_bold_charmap = {}
for c in helv_charmap.keys():
    helv_bold_charmap[c] = helv_charmap[c]

def fill_hfm(psz, clist):
    for c in clist: helv_bold_charmap[c]=psz

fill_hfm(3.3344, "'`ijl")
fill_hfm(3.3585, '|')
fill_hfm(3.9942, '!:;[]ft')
fill_hfm(4.6658, 'r{}')
fill_hfm(5.6854, '"')
fill_hfm(6.6689, 'Jcksvxy')
fill_hfm(7.0048, '^')
fill_hfm(7.3286, '?Lbdghnopqu')
fill_hfm(8.6600, '&ABK')
fill_hfm(9.3317, 'w')
fill_hfm(10.6631, 'm')
fill_hfm(11.6946, '@')

font_metrics['Helvetica-Bold'] = helv_bold_charmap

# Mappings between HTML header tags and font sizes
# The values used by Mosaic
#font_sizes = {
#    None: 12,
#    'h1': 36,
#    'h2': 24,
#    'h3': 18,
#    'h4': 14,
#    'h5': 12,
#    'h6': 10
#    }

# The values used by Grail
font_sizes = {
    None: 12,
    'h1': 18,
    'h2': 14,
    'h3': 12,
    'h4': 10,
    'h5': 10,
    'h6': 10
    }


# Ruler stuff, not used...
#ruler = [1, 16, 8, 16, 4, 16, 8, 16, 2, 16, 8, 16, 4, 16, 8, 16]
#ruler = map(lambda(x): 72.0/(x*2.0), ruler)



# Page layout and other contants.  Some of this stuff is carried over
# from HTML-PSformat.c and perhaps no longer relevent

# Regular expressions.
CR = '\015'
LF = '\012'
CRLF_re = '%c\\|%c' % (CR, LF)

L_PAREN = '('
R_PAREN = ')'
B_SLASH = '\\\\'
QUOTE_re = '\\(%c\\|%c\\|%s\\)' % (L_PAREN, R_PAREN, B_SLASH)

MAX_ASCII = '\177'

# the next page sizes are a compromise between letter sized paper
# (215.9 x 279.4 mm) and european standard A4 sized paper (210.0 x
# 297.0 mm).  Note that PAGE_WIDTH is not the actual width of the
# paper

def inch_to_pt(inches): return inches * 72.0
def pt_to_inch(points): return points / 72.0

TOP_MARGIN = inch_to_pt(10)
BOT_MARGIN = inch_to_pt(0.5)
LEFT_MARGIN = inch_to_pt(0.75)
RIGHT_MARGIN = inch_to_pt(1.0)
PAGE_HEIGHT = (TOP_MARGIN - 2 * BOT_MARGIN)
PAGE_WIDTH = inch_to_pt(8.5) - LEFT_MARGIN - RIGHT_MARGIN

# horizontal rule spacing, in points
HR_TOP_MARGIN = 8.0
HR_BOT_MARGIN = 8.0 

# distance after a label tag in points
LABEL_TAB = 8.0

# page indicator yposition
PAGE_TAB = -PAGE_HEIGHT - 32

# I don't support color yet
F_FULLCOLOR = 0
F_GREYSCALE = 1
F_BWDITHER = 2
F_REDUCED = 3



class PSFont:
    """This class manages font changes and calculation of associated
    metrics for PostScript output.  It basically defines a mapping
    between a PostScript definition for a font and a short name used
    by PostScript functions defined in the header template.

    When the font is created, it is passed the name of a variable
    width family and a fixed width family.  Those are the only
    configuration options you have.  Should probably allow a scaling
    factor to be passed in, mapping GUI dpi to PostScript dpi, but
    that would have to be calculated by Grail for the underlying GUI.

    Exported methods:

       __init__(optional: VARIFAMILY, FIXEDFAMILY)
       set_font((SIZE, ITALIC?, BOLD?, TT?)) ==> (PSFONTNAME, SIZE)
       text_width(TEXT) ==> WIDTH_IN_POINTS
       font_size(optional: (SIZE, ITALIC?, BOLD?, TT?)) ==> SZ_IN_POINTS

    Exported ivars:

       space_width  --> width in points of a single space

    """
    def __init__(self, varifamily='Helvetica', fixedfamily='Courier'):
	"""Create a font definition using VARIFAMILY as the variable
	width font and FIXEDFAMILY as the fixed width font.  Defaults
	to Helvetica and Courier respectively.
	"""
	# current font is a tuple of size, family, italic, bold
	self.vfamily = varifamily
	self.ffamily = fixedfamily
	self.font = (12, 'FONTV', '', '')

	# TBD: this number is slightly bogus, but the rational is
	# thus.  The original code was tied fairly closely with X so
	# it had to map screen resolutions to PostScript.  I don't
	# want this version to be tied to X at all, if possible, so I
	# ignore all screen resolution parameters.  The tradeoff is
	# that the hardcopy will probably not be formatted exactly as
	# it appears on the screen, but I believe that is appropriate.
	# Should we decide to change that, this scaling factor may
	# come into play, but should probably be passed in from Grail,
	# since only it can interface to the underlying window system.
	self.points_per_pixel = 72.0 / 72.0

	# calculate document fonts
	if not fonts.has_key(self.vfamily): self.vfamily = 'Helvetica'
	if not fonts.has_key(self.ffamily): self.ffamily = 'Courier'
	vrealname, vreg, vbold, vitalic = fonts[self.vfamily]
	frealname, freg, fbold, fitalic = fonts[self.ffamily]
	# fonts may be mapped to other fonts
	if not vrealname: vrealname = self.vfamily
	if not frealname: frealname = self.ffamily

	# gather appropriate bold and non-bold metrics
	try: fmetrics = font_metrics[frealname]
	except KeyError: fmetrics = font_metrics['Courier']

	try: vmetrics = font_metrics[vrealname]
	except KeyError: vmetrics = font_metrics['Helvetica']
	
	try: vbmetrics = font_metrics[vrealname + '-Bold']
	except KeyError: vbmetrics = font_metrics['Helvetica-Bold']

	self.metrics = {
	    'FONTF': fmetrics,
	    'FONTV': vmetrics,
	    'FONTFB': fmetrics,
	    'FONTVB': vbmetrics
	    }

	# calculate font names in PostScript space. Eight fonts are
	# used, naming scheme is as follows.  All PostScript font
	# name definitions start with `FONT', followed by `V' for the
	# variable width font and `F' for the fixed width font.  `B'
	# for the bold version, `I' for italics, and for the
	# bold-italic version, `B' *must* preceed `I'.  See
	# header_template below for more info.
	self.docfonts = {
	    'FONTV':   '%s%s' % (vrealname, vreg),
	    'FONTVB':  '%s-%s' % (vrealname, vbold),
	    'FONTVI':  '%s-%s' % (vrealname, vitalic),
	    'FONTVBI': '%s-%s%s' % (vrealname, vbold, vitalic),
	    'FONTF':   '%s%s' % (frealname, freg),
	    'FONTFB':  '%s-%s' % (frealname, fbold),
	    'FONTFI':  '%s-%s' % (frealname, fitalic),
	    'FONTFBI': '%s-%s%s' % (frealname, fbold, fitalic)
	    }
	# set the default font
	self.set_font((12, 'FONTV', '', ''))

    def set_font(self, font_tuple):
	"""Set the current font to that specified by FONT_TUPLE, which
	is of the form (SIZE, ITALIC?, BOLD?, TT?).  Returns the
	PostScript layer name of the font, and the font size in
	points.  """
	# we *said* we wanted a tuple
	if font_tuple is None: font_tuple = (None, None, None, None)
	# get the current font and break up the tuple
	cur_sz, cur_family, cur_italic, cur_bold = self.font
	set_sz, set_italic, set_bold, set_tt = font_tuple
	# calculate size
	new_sz = self.font_size(font_tuple)
	# calculate variable vs. fixed base name
	if set_tt: new_family = 'FONTF'
	else: new_family = 'FONTV'

	# add modifiers.  Because of the way fonts are named, always
	# add bold modifier before italics modifier, in case both are
	# present
	if set_bold: new_bold = 'B'
	else: new_bold = ''

	# do this before we add the italics modifier, since italics
	# doesn't contribute to metrics
	self.metric = self.metrics[new_family + new_bold]

	if set_italic: new_italic = 'I'
	else: new_italic = ''

	# save the current font specification
	self.font = (new_sz, new_family, new_italic, new_bold)

	# set the font
	font = '%s%s%s' % (new_family, new_bold, new_italic)
	# set the width of a space, an oft used `constant'
	self.space_width = self.text_width(' ')
	# return the PostScript font definition and the size in points
	return (font, new_sz)

    def text_width(self, text):
	"""Calculate the width of the given TEXT in points using the
	current font size and metrics.
	"""
	# optimization for fixed width fonts
	if type(self.metric) == type(1.0):
	    return len(text) * self.metric * self.font[0] / 12.0
	else:
	    pointlen = 0.0
	    for c in text:
		try: charmetric = self.metric[c]
		except KeyError: charmetric = 0.0
		pointlen = pointlen + charmetric
	    return pointlen * self.font_size() / 12.0

    def font_size(self, font_tuple=None):
	"""Return the size of the current font, or the font defined by
	optional FONT_TUPLE if present."""
	if not font_tuple: return self.font[0]
	tuple_sz = font_tuple[0]
	try:
	    if type(tuple_sz) != type(1): return font_sizes[tuple_sz]
	    else: return tuple_sz
	except KeyError: return 12



# PSQueue class contains a queue of high level directives to the
# PostScript generator.  This is necessary because some things you
# just can't calculate until you've seen the end of the current line
# (e.g. the vertical tab distance).  We actually make 3 passes through
# the queue of directives.  The first just populates them via stream
# of (Grail) consciousness... i.e. the PSWriter interface.  Next, we
# scan through the queue generating such things as line breaks and
# other non-linear directives.  Finally we cruise through the queue
# generating PostScript code for each directive we find.  Turns out
# not to be too slow, and it is very flexible and easy to add new
# directives.

tag_consts = """
START = 0
STRING = 1
FONT_CHANGE = 2
SPACE = 3
HR = 4
UNDERLINE = 5
LITERAL = 6
HARD_NL = 7
VERT_TAB = 8
PAGE_BREAK = 9
MARGIN = 10
LABEL = 11
END = 100
"""
exec tag_consts
tags = {}
exec tag_consts in tags
for key, value in tags.items():
    if key != '__builtins__':
	tags[value] = key



class PSQueue:
    """Class PSQueue manages a queue of high level PostScript
    rendering directives as fed from the PSWriter interface to
    AbstractWriter.  Because of complexities of PostScript generation,
    two passes are made through the queue after initial population.
    First the queue is scanned for line breaks and other non-linear
    directives, and then it is scanned for direct translation to
    PostScript code.

    Exported methods:

       __init__(PSFont_instance, OutputFileObject, optional: TITLE_STRING)
       push_string(STRING)
       push_font_change(FONT_TUPLE)
       push_space(NUMBER_OF_SPACES)
       push_horiz_rule()
       push_end()
       push_margin(INDENTATION_LEVEL)
       push_label(BULLET_TAG)
       push_hard_newline(NUMBER_OF_NEWLINES)
       push_vtab(DISTANCE_IN_POINTS, optional:QUEUE_MARK)
       push_underline(FLAG)
       push_literal(FLAG)
       mark() ==> QUEUE_MARK
       pop(optional: TAG_TO_MATCH) ==> TOP_OF_QUEUE or None
       break_lines()
       write_to_postscript()

    Exported ivars:
    """
    def __init__(self, psfont, ofile, title=''):
	self.queue = [(START, title)]
	self.font = psfont
	self.ofile = ofile
	self.title = title
	self.curpage = 1
	self.margin = 0.0

    def push_string(self, string):
	tag, info = self.pop(STRING)
	if tag: string = info + string
	self.queue.append((STRING, string))

    def push_font_change(self, font):
	tag, info = self.pop(FONT_CHANGE)
	# doesn't make much sense to have 2 font changes in a row
	self.queue.append((FONT_CHANGE, font))

    def push_space(self, spaces=1):
	tag, info = self.pop(SPACE)
	if tag: spaces = spaces + info
	self.queue.append((SPACE, spaces))

    def push_horiz_rule(self): self.queue.append((HR, None))
    def push_end(self): self.queue.append((END, None))
    def push_margin(self, level): self.queue.append((MARGIN, level))
    def push_label(self, bullet): self.queue.append((LABEL, bullet))

    def push_hard_newline(self, blanklines=1):
	tag, info = self.pop(HARD_NL)
	if tag: blanklines = blanklines + info
	self.queue.append((HARD_NL, blanklines))

    def push_vtab(self, distance, atmark=None):
	"""Push a VERT_TAB directive onto the queue, providing the
	vertical DISTANCE in points.

	Optional ATMARK is a queue mark as returned by the mark()
	method, indicating a position into the queue at which to
	insert the VERT_TAB directive.  Otherwise, append it to the
	end of the queue.
	"""
	tag, info = self.pop(VERT_TAB)
	if tag: distance = distance + info
	if atmark: self.queue.insert(atmark, (VERT_TAB, distance))
	else: self.queue.append((VERT_TAB, distance))

    def push_underline(self, flag):
	tag, info = self.pop(UNDERLINE)
	# doesn't make much sense to have 2 render changes in a row
	self.queue.append((UNDERLINE, flag))

    def push_literal(self, flag):
	tag, info = self.pop(LITERAL)
	# doesn't make much sense to have 2 literal state changes in a row
	self.queue.append((LITERAL, flag))


    def mark(self):
	"""Return a queue mark, marking the current end of the queue.
	This is appropriate for non-append inserts into the queue, if
	the push_() method used supports inserts.
	"""
	return len(self.queue)

    def pop(self, tagmatch=None):
	"""Pops the last element off of the queue and returns it.  If
	an error occurs (i.e. the queue is empty), it returns the
	tuple (None, None).

	With optional TAGMATCH, only pop and return the last element
	if its tag matches TAGMATCH, otherwise do not pop and return
	(None, None).
	"""
	try:
	    if not tagmatch or tagmatch == self.queue[-1][0]:
		rtn = self.queue[-1]
		del self.queue[-1]
		return rtn
	    else: return (None, None)
	except IndexError: return (None, None)

    def break_lines(self):
	"""Perform first pass through directive queue.  You *must*
	call this before calling write_to_postscript().
	"""
	nq = PSQueue(self.font, self.ofile, self.title)
	xpos = 0.0
	tallest = self.font.font_size()
	in_literal_p = 0
	for tag, info in self.queue:
	    #debug('breaking: (%s, %s)\n' % (tags[tag], info))
	    if tag == START:
		nq.push_font_change(None)
		self.font.set_font(None)
		mark = nq.mark()
	    elif tag == END:
		nq.push_vtab(tallest * 1.1, mark)
		nq.push_end()
	    elif tag == UNDERLINE:
		nq.push_underline(info)
	    elif tag == FONT_CHANGE:
		tallest = max(tallest, self.font.font_size())
		nq.push_font_change(info)
		self.font.set_font(info)
	    elif tag == HARD_NL:
		nq.push_vtab(tallest * 1.1, mark)
		if info > 1:
		    nq.push_vtab(tallest * 1.1 * (info - 1))
		nq.push_hard_newline(info)
		xpos = 0.0
		tallest = 0
		mark = nq.mark()
	    elif tag == HR:
		nq.push_vtab(tallest * 1.1, mark)
		nq.push_vtab(HR_TOP_MARGIN)
		nq.push_horiz_rule()
		nq.push_vtab(HR_BOT_MARGIN)
		nq.push_hard_newline(1)
		mark = nq.mark()
		xpos = 0.0
	    elif tag == MARGIN:
		nq.push_margin(info)
		self.margin = info * LEFT_MARGIN
	    elif tag == LABEL:
		if info is not None:
		    info = self.font.text_width(info) + LABEL_TAB
		nq.push_label(info)
	    elif tag == LITERAL:
		if in_literal_p != info:
		    in_literal_p = info
		    nq.push_literal(info)
	    elif tag == SPACE:
		# spaces at the beginning of the line are thrown away,
		# unless we are in literal text
		if in_literal_p or xpos > 0.0:
		    xpos = xpos + (self.font.space_width * info)
		    nq.push_space(info)
	    elif tag == STRING:
		if xpos == 0.0:
		    tallest = self.font.font_size()
		swidth = self.font.text_width(info)
		ltag, linfo = nq.pop(SPACE)
		if xpos + swidth + self.margin < PAGE_WIDTH:
		    # okay, so the text fits, but if the preceding
		    # node is a space, then they can both be collapsed
		    # into a single STRING node
		    xpos = xpos + swidth
		    # push_string will take care of collapsing any
		    # preceding strings into this one
		    if ltag:
			info = ' ' * linfo + info
		    nq.push_string(info)
		    continue
		# the new text doesn't fit on the line so we can do a
		# simple break of the line if the previous tag we saw
		# was a space, and the current line width is > 3/4 of
		# the page width and the current text is smaller than
		# the page width
		if ltag and \
		     xpos + self.margin > PAGE_WIDTH * 0.75 and \
		     swidth < PAGE_WIDTH:
		    # note that we can ignore the line trailing spaces
		    nq.push_vtab(tallest * 1.1, mark)
		    nq.push_hard_newline()
		    mark = nq.mark()
		    nq.push_string(info)
		    xpos = swidth
		# we have bigger problems, because if the last thing
		# we saw was a space, then we'll have to break the
		# word in the middle someplace.  for now we'll just
		# let it overflow.  TBD: fix this!
	        else:
		    nq.push_string(info)
	# replace our queue with the collapsed queue
	self.queue = nq.queue

    def write_to_postscript(self):
	"""Second pass through directive queue.  Actually generates
	PostScript output based on the directives it finds.  Note that
	you *must* call break_lines() before calling this method.
	"""
	# now scan through the queue
	render_cmd = 'S'
	ypos = 0.0
	for tag, info in self.queue:
	    #debug('writing: (%s, %s)\n' % (tags[tag], info))
	    if tag == START:
		self._header(info)
		self._start_page(self.curpage)
	    elif tag == STRING:
		# handle quoted characters
		cooked = regsub.gsub(QUOTE_re, '\\\\\\1', info)
		# TBD: handle ISO encodings
		pass
		self.ofile.write('(%s) %s\n' % (cooked, render_cmd))
	    elif tag == SPACE:
		self.ofile.write('(%s) %s\n' % (' ' * info, render_cmd))
	    elif tag == FONT_CHANGE:
		psfontname, size = self.font.set_font(info)
		self.ofile.write('%s %d SF\n' % (psfontname, size))
	    elif tag == UNDERLINE:
		render_cmd = info and 'U' or 'S'
	    elif tag == HR:
		self.ofile.write('%f HR\n' % PAGE_WIDTH)
	    elif tag == MARGIN:
		self.ofile.write('/indentmargin %f D\n' % (info * LEFT_MARGIN))
		self.ofile.write('NL\n')
	    elif tag == LABEL:
		if info is not None:
		    self.ofile.write('gsave NL -%f 0 R\n' % info)
		else:
		    self.ofile.write('grestore\n')
	    elif tag == LITERAL:
		pass
	    elif tag == VERT_TAB:
		ypos = ypos - info
		if ypos <= -PAGE_HEIGHT:
		    self._end_page()
		    self.curpage = self.curpage + 1
		    self._start_page(self.curpage)
		    ypos = 0.0
		self.ofile.write('0 -%f R\n' % info)
	    elif tag == HARD_NL:
		self.ofile.write('NL\n')
	    elif tag == END:
		self._trailer()

    def _start_page(self, pagenum):
	stdout = sys.stdout
	try:
	    sys.stdout = self.ofile
	    # write the structure page convention
	    print '%%Page:', pagenum, pagenum
	    print 'save'
	    print 'NP'
	    print '0 0 M NL'
	    if RECT_DEBUG:
		print 'gsave', 0, 0, "M"
		print PAGE_WIDTH, 0, "RL"
		print 0, -PAGE_HEIGHT, "RL"
		print -PAGE_WIDTH, 0, "RL closepath stroke newpath"
		print 'grestore'
	finally:
	    sys.stdout = stdout


    def _end_page(self, trailer=0):
	stdout = sys.stdout
	try:
	    sys.stdout = self.ofile
	    print 'save', 0, PAGE_TAB, "M"
	    print "FONTVI 12 SF"
	    print "(Page", self.curpage, ") C restore"
	    print "showpage"
	finally:
	    sys.stdout = stdout

    def _header(self, title=None):
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.ofile
	    print "%!PS-Adobe-1.0"
	    if title:
		# replace all cr/lf's with spaces
		title = regsub.gsub(CRLF_re, ' ', title)
		print "%%Title:", title

	    # output font prolog
	    docfonts = self.font.docfonts
	    print "%%DocumentFonts:",
	    for dfv in docfonts.values(): print dfv,
	    print

	    # spew out the contents of the header PostScript file
	    print header_template
	    # define the fonts
	    for docfont in docfonts.keys():
		print "/%s" % docfont, "{/%s}" % docfonts[docfont], "D"

	    # swew out ISO encodings
	    print iso_template
	    # finish out the prolog
	    print "/xmargin", LEFT_MARGIN, "D"
	    print "/topmargin", TOP_MARGIN, "D"
	    print "/indentmargin", 0.0, "D"
	    print "/pagewidth", PAGE_WIDTH, "D"
	    print "/scalfac", self.font.points_per_pixel, "D"
	    print "%%EndProlog"
	finally:
	    sys.stdout = oldstdout
	    
    def _trailer(self):
	self._end_page(1)
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.ofile
	    print "%%Trailer"
	    print "restore"
	    print "%%Pages:", self.curpage
	finally:
	    sys.stdout = oldstdout



class PSWriter(AbstractWriter):
    """Class PSWriter supports the backend interface expected by
    Grail, actually the HTMLParser class.  It does this by deriving
    from AbstractWriter and overriding methods to interface with the
    PSQueue class, which performs the real PostScript work.

    Exported methods:

      __init__(OUTPUT_FILE_OBJECT, optional:TITLE)
      close()
      new_font(FONT_TUPLE)
      new_margin(MARGIN_TAG(ignored) LEVEL)
      new_spacing(SPACING)
      new_styles(STYLE_TUPLE)
      send_paragraph(NUMBER_OF_BLANKLINES)
      send_line_break()
      send_hor_rule()
      send_label_data(LABEL_TAG)
      send_flowing_data(TEXT)
      send_literal_data(TEXT)

    Exported ivars:
    """
    def __init__(self, ofile, title=''):
	font = PSFont()
	self.ps = PSQueue(font, ofile, title)

    def close(self):
	self.ps.push_end()
	self.ps.break_lines()
	self.ps.write_to_postscript()

    def new_font(self, font):
	self.ps.push_font_change(font)

    def new_margin(self, margin, level):
	self.ps.push_margin(level)

    def new_spacing(self, spacing):
	#print "new_spacing(%s)" % `spacing`
	raise RuntimeError

    def new_styles(self, styles):
	# semantics of STYLES is a tuple of single char strings.
	# Right now the only styles we support are lower case 'u' for
	# underline.
	if 'u' in styles:
	    self.ps.push_underline(1)
	else:
	    self.ps.push_underline(0)

    def send_paragraph(self, blankline):
	for nl in range(blankline+1):
	    self.ps.push_hard_newline()

    def send_line_break(self):
	self.ps.push_hard_newline()
	self.ps.push_hard_newline()

    def send_hor_rule(self):
	self.ps.push_horiz_rule()

    def send_label_data(self, data):
	self.ps.push_label(data)
	self.ps.push_string(data)
	self.ps.push_label(None)

    def send_flowing_data(self, data):
	self.ps.push_literal(0)
	self._write_text(data)

    def send_literal_data(self, data):
	self.ps.push_literal(1)
	self._write_text(data)

    def _write_text(self, data):
	lines = string.splitfields(data, '\n')
	linecnt = len(lines)-1
	for line in lines:
	    words = string.splitfields(line, ' ')
	    wordcnt = len(words)-1
	    for word in words:
		self.ps.push_string(word)
		if wordcnt > 0: self.ps.push_space()
		wordcnt = wordcnt - 1
	    if linecnt > 0: self.ps.push_hard_newline()
	    linecnt = linecnt - 1


def html_test():
    import getopt
    import os
    help = None
    error = None
    options = []
    infile = None
    outfile = None
    logfile = None
    try: options, argv = getopt.getopt(sys.argv[1:], 'hdl:i:o:')
    except getopt.error: error = 1; help = 1
    for o, a in options:
	if o == '-h': help = 1		# help
	elif o == '-d': DEBUG = 1	# debugging, obviously ;-)
	elif o == '-l':			# debug log file, otherwise stderr
	    logfile = a
	elif o == '-i':			# input file, otherwise stdin
	    infile = a
	elif o == '-o':			# output file, otherwise stdout
	    outfile = a
    if help:
	stdout = sys.stderr
	print 'Usage:', sys.argv[0], \
	      '[-d] [-l <logfile>] [-i <infile>] [-o <outfile>] [-h]'
	if error: sys.exit(1)
	sys.exit(0)

    ifile = None
    if infile:
	try: ifile = open(infile, 'r')
	except IOError: pass
    ofile = None
    if outfile:
	try: ofile = open(outfile, 'w')
	except IOError: pass
    lfile = None
    if logfile:
	try: lfile = open(logfile, 'w')
	except IOError: pass

    if not ifile:
	# use this as a filter
	ifile = sys.stdin
	ofile = sys.stdout
	lfile = sys.stderr
    elif not ofile:
	# output file can be derived from input file
	outfile = os.path.splitext(infile)[0] + '.ps'
	try: ofile = open(outfile, 'w')
	except IOError: ofile = sys.stdout
	
    stderr = sys.stderr
    try:
	if lfile: sys.stderr = lfile
	w = PSWriter(ofile, None)
	f = AbstractFormatter(w)

	# We don't want to be dependent on Grail, but we do want to
	# use it if it's around.  Only current difference is that
	# links are underlined with the PrintDialog parser.
	try:
	    import PrintDialog
	    p = PrintDialog.PrintingHTMLParser(f)
	except:
	    import htmllib
	    p = htmllib.HTMLParser(f)

	p.feed(ifile.read())
	p.close()
	w.close()
    finally:
	sys.stderr = stderr



# Line length test
def lltest():
    w = PSWriter(sys.stdout)
    ff = PSFont()
    font = (12, None, 1, None)
    w.new_font(font)
    ff.set_font(font)
    for c in range(32,127):
	c = chr(c)
	l = ff.text_width(c)
	count = int(PAGE_WIDTH / l)
	msg = c * count
	w.send_literal_data(msg)
	w.send_literal_data('|')
	w.send_label_data(repr(count))
	w.send_line_break()
    w.close()


# PostScript templates
header_template = """
%%Creator: CNRI Grail, HTML2PS.PY by Barry Warsaw
%%   Adapted from the Public Domain NCSA Mosaic,
%%   Postscript templates by Ameet Raval & Frans van Hoesel
%%Pages: (atend)
%%EndComments
save
/D {def} def
/E {exch} D
/M {moveto} D
/S {show} D
%/S {dup show ( ) show stringwidth pop 20 string cvs show} D
/C {dup stringwidth pop pagewidth exch sub 2 div 0 rmoveto show} D
/R {rmoveto} D
/L {lineto} D
/RL {rlineto} D
/NL {indentmargin currentpoint E pop M} D
/SQ {newpath 0 0 M 0 1 L 1 1 L 1 0 L closepath} D
/U {
  gsave currentpoint currentfont /FontInfo get /UnderlinePosition get
  0 E currentfont /FontMatrix get dtransform E pop add newpath moveto
  dup stringwidth rlineto stroke grestore S
} D
/B {
  /r E D gsave -13 0  R currentpoint 
  newpath r 0 360 arc closepath fill grestore
} D
/OB {
  /r E D gsave -13 0  R currentpoint 
  newpath r 0 360 arc closepath stroke grestore
} D
/NP {xmargin topmargin translate scalfac dup scale } D
/HDR {1 1 scale} D
/HR {/l E D gsave currentpoint 0 E M pop l 0 RL  stroke grestore } D
/SF {E findfont E scalefont setfont } D
"""

iso_template = """
% PSinit_latin1 - handle ISO encoding
%
% print out initializing PostScript text for ISO Latin1 font encoding
% This code is copied from the Idraw program (from Stanford's InterViews 
% package), courtesy of Steinar Kjaernsr|d, steinar@ifi.uio.no

/reencodeISO {
  dup dup findfont dup length dict begin
    { 1 index /FID ne { def }{ pop pop } ifelse } forall
    /Encoding ISOLatin1Encoding D
    currentdict end definefont
    } D
/ISOLatin1Encoding [
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /space/exclam/quotedbl/numbersign/dollar/percent/ampersand/quoteright
  /parenleft/parenright/asterisk/plus/comma/minus/period/slash
  /zero/one/two/three/four/five/six/seven/eight/nine/colon/semicolon
  /less/equal/greater/question/at/A/B/C/D/E/F/G/H/I/J/K/L/M/N
  /O/P/Q/R/S/T/U/V/W/X/Y/Z/bracketleft/backslash/bracketright
  /asciicircum/underscore/quoteleft/a/b/c/d/e/f/g/h/i/j/k/l/m
  /n/o/p/q/r/s/t/u/v/w/x/y/z/braceleft/bar/braceright/asciitilde
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef/.notdef
  /.notdef/dotlessi/grave/acute/circumflex/tilde/macron/breve
  /dotaccent/dieresis/.notdef/ring/cedilla/.notdef/hungarumlaut
  /ogonek/caron/space/exclamdown/cent/sterling/currency/yen/brokenbar
  /section/dieresis/copyright/ordfeminine/guillemotleft/logicalnot
  /hyphen/registered/macron/degree/plusminus/twosuperior/threesuperior
  /acute/mu/paragraph/periodcentered/cedilla/onesuperior/ordmasculine
  /guillemotright/onequarter/onehalf/threequarters/questiondown
  /Agrave/Aacute/Acircumflex/Atilde/Adieresis/Aring/AE/Ccedilla
  /Egrave/Eacute/Ecircumflex/Edieresis/Igrave/Iacute/Icircumflex
  /Idieresis/Eth/Ntilde/Ograve/Oacute/Ocircumflex/Otilde/Odieresis
  /multiply/Oslash/Ugrave/Uacute/Ucircumflex/Udieresis/Yacute
  /Thorn/germandbls/agrave/aacute/acircumflex/atilde/adieresis
  /aring/ae/ccedilla/egrave/eacute/ecircumflex/edieresis/igrave
  /iacute/icircumflex/idieresis/eth/ntilde/ograve/oacute/ocircumflex
  /otilde/odieresis/divide/oslash/ugrave/uacute/ucircumflex/udieresis
  /yacute/thorn/ydieresis
] D
[FONTV FONTVB FONTVI FONTVBI FONTF FONTFB FONTFI FONTFBI] {
  reencodeISO D
} forall
"""


if __name__ == '__main__':
    html_test()
