"""HTML to PostScript translator.

This module uses the AbstractWriter class interface defined by Grail
to generate PostScript corresponding to a stream of HTML text.  The
HTMLParser class scans the HTML stream, generating high-level calls to
an AbstractWriter object.  This module defines a class derived from
AbstractWriter, called PSWriter, that supports this high level
interface as appropriate for PostScript generation.
"""

__version__ = "$Id: html2ps.py,v 1.11 1995/09/14 20:03:07 bwarsaw Exp $"

import sys
import string
import StringIO
import regsub
from formatter import *

RECT_DEBUG = 0
DEBUG = 0
LP_COMMAND = 'lp -d tps'

def _debug(text):
    if DEBUG:
	sys.stderr.write(text)
	sys.stderr.flush()


# Font Dictionary.  Key is the short name describing the font, value
# is a 5-tuple indicating the real name of the font, then the regular,
# bold, and italic modifiers of the font.  Note that if their is no
# regular name modifier, then use the empty string, but if there is a
# regular name modifier, make sure it includes a leading dash.  Other
# modifiers should not include the dash.
fonts = {
    'Times':            (None, '-Roman', 'Bold', 'Italic'),
    'Helvetica':        (None, '',       'Bold', 'Oblique'),
    'NewCenturySchlbk': (None, '-Roman', 'Bold', 'Italic'),
    'Courier':          (None, '',       'Bold', 'Oblique'),
    # The code from HTML-PSformat.c says:
    # "This is a nasty trick, I have put Times in place of Lucida,
    # because most printers don't have Lucida font"
    # Hmm...
    #'Lucida':           ('Times', None, 'Bold', 'Italic'),
    'Lucida':           (None, '', 'Bold', 'Italic'),
    }

# contains mappings of font family to font metrics dictionary.  each
# dictionary contains a mapping between characters in the 0-256 range
# and their widths in points.  it is assumed that different font sizes
# scale these widths linearly
font_metrics = {}

# 12 point, fixed width font metrics, all chars are the same width.
# for speed, I'll actually implement this differently
#courier_charmap = {}
#for c in range(256): courier_charmap[c] = 7.2
#font_metrics['Courier'] = courier_charmap
font_metrics['Courier'] = 7.2

helv_charmap = {}
def fill_hfm(clist, psz):
    for c in clist: helv_charmap[c] = psz

fill_hfm(range(31), 0.0)
fill_hfm(range(128,256), 0.0)
fill_hfm([' ', '!', ',', '.', '/', ':', ';', 'I', '[', '\\', ']', 'f', 't'],
	 3.375)
fill_hfm(['"'], 4.3875)
fill_hfm(['#', '$', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
	  '?', 'L', '_', 'a', 'b', 'd', 'e', 'g', 'h', 'n', 'o', 'p', 'q',
	  'u'],
	 6.75)
fill_hfm(['%'], 10.8)
fill_hfm(['&', 'A', 'B', 'E', 'K', 'P', 'S', 'V', 'X', 'Y'], 8.1)
fill_hfm(["'", '`', 'i', 'j', 'l'], 2.7)
fill_hfm(['(', ')', 'r', '{', '}'], 4.05)
fill_hfm(['*'], 4.725)
fill_hfm(['+', '-', '<', '=', '>', '~'], 7.0875)
fill_hfm(['@'], 12.2625)
fill_hfm(['C', 'D', 'H', 'N', 'R', 'U', 'w'], 8.775)
fill_hfm(['F', 'Z'], 7.65)
fill_hfm(['G', 'O', 'Q'], 9.45)
fill_hfm(['J', 'c', 'k', 's', 'v', 'x', 'y', 'z'], 6.075)
fill_hfm(['M', 'm'], 10.125)
fill_hfm(['W'], 11.475)
fill_hfm(['T'], 7.425)
fill_hfm(['^'], 5.7375)
fill_hfm(['|'], 3.15)

# sanity check
#for c in range(32, 127):
#    width = helv_charmap[chr(c)]
#    if width is None or width <= 0:
#	raise KeyError, c
font_metrics['Helvetica'] = helv_charmap

# some of the Helvetica Bold characters are a bit wider than their
# non-bold parallels.
helv_bold_charmap = {}
for c in helv_charmap.keys():
    helv_bold_charmap[c] = helv_charmap[c]

def fill_hbfm(clist, psz):
    for c in clist: helv_bold_charmap[c] = psz

fill_hbfm(['!', ':', ';', '[', ']', 'f', 't'], 4.05)
fill_hbfm(['"'], 5.7375)
fill_hbfm(['&', 'A', 'B', 'K'], 8.775)
fill_hbfm(["'", '`', 'i', 'j', 'l'], 3.375)
fill_hbfm(['?', 'L', 'b', 'd', 'g', 'h', 'n', 'o', 'p', 'q', 'u'], 7.425)
fill_hbfm(['@'], 11.7)
fill_hbfm(['J', 'c', 'k', 's', 'v', 'x', 'y'], 6.75)
fill_hbfm(['^'], 7.0875)
fill_hbfm(['m'], 10.8)
fill_hbfm(['r', '{', '}'], 4.725)
fill_hbfm(['w'], 9.45)
fill_hbfm(['|'], 3.4875)

font_metrics['Helvetica-Bold'] = helv_bold_charmap


font_sizes = {
    None: 12,
    'h1': 36,
    'h2': 24,
    'h3': 18,
    'h4': 14,
    'h5': 12,
    'h6': 10
    }


ruler = [1, 16, 8, 16, 4, 16, 8, 16, 2, 16, 8, 16, 4, 16, 8, 16]
ruler = map(lambda(x): 72.0/(x*2.0), ruler)


# contants
FONT_METRIC_SCALE_FACTOR = 0.9
PS_HEADER_FILE = 'header.ps'
ISO_LATIN1_FILE = 'latin1.ps'
CR = '\015'
LF = '\012'
CRLF_re = '%c\\|%c' % (CR, LF)


# the next page sizes are a compromise between letter sized paper
# (215.9 x 279.4 mm) and european standard A4 sized paper (210.0 x
# 297.0 mm).  Note that PAGE_WIDTH is not the actual width of the
# paper

def inch_to_pt(inches): return inches * 72.0
def pt_to_inch(points): return points / 72.0

TOP_MARGIN = inch_to_pt(10)
BOT_MARGIN = inch_to_pt(0.5)
LEFT_MARGIN = inch_to_pt(1.0)
RIGHT_MARGIN = inch_to_pt(1.0)
PAGE_HEIGHT = (TOP_MARGIN - 2 * BOT_MARGIN)
PAGE_WIDTH = inch_to_pt(8.5) - 2 * LEFT_MARGIN

# horizontal rule spacing, in points
HR_TOP_MARGIN = 8.0
HR_BOT_MARGIN = 8.0 

# distance after a label tag in points
LABEL_TAB = 8.0

F_FULLCOLOR = 0
F_GREYSCALE = 1
F_BWDITHER = 2
F_REDUCED = 3

L_PAREN = '('
R_PAREN = ')'
B_SLASH = '\\\\'
QUOTE_re = '\\(%c\\|%c\\|%s\\)' % (L_PAREN, R_PAREN, B_SLASH)

MAX_ASCII = '\177'



class PSFont:
    """Manages fonts and associated metrics for PostScript output."""
    def __init__(self, varifamily='Helvetica', fixedfamily='Courier'):
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
	# come into play.
	self.points_per_pixel = 72.0 / 72.0
	# calculate document fonts
	if not fonts.has_key(self.vfamily): self.vfamily = 'Helvetica'
	if not fonts.has_key(self.ffamily): self.ffamily = 'Courier'
	vrealname, vreg, vbold, vitalic = fonts[self.vfamily]
	frealname, freg, fbold, fitalic = fonts[self.ffamily]
	# fonts may be mapped to other fonts
	if not vrealname: vrealname = self.vfamily
	if not frealname: frealname = self.ffamily
	# gather appropriate metrics
	try: fmetrics = font_metrics[frealname]
	except KeyError: fmetrics = font_metrics['Courier']

	if vbold:
	    vmetricname = vrealname + '-Bold'
	    if not font_metrics.has_key(vmetricname):
		vmetricname = 'Helvetica-Bold'
	    vmetrics = font_metrics[vmetricname]
	else:
	    try: vmetrics = font_metrics[vrealname]
	    except KeyError: vmetrics = font_metrics['Helvetica']
	self.metrics = (vmetrics, fmetrics)
	# calculate font names in PostScript space. Eight fonts are
	# used, naming scheme is as follows.  All PostScript font
	# name definitions start with `FONT', followed by `V' for the
	# variable width font and `F' for the fixed width font.  `B'
	# for the bold version, `I' for italics, and for the
	# bold-italic version, `B' *must* preceed `I'
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
	"""Set the current font to that specified by FONT_TUPLE, which is
	of the form (SIZE, ITALIC-P, BOLD-P, TT-P).  Returns the
	PostScript layer name of the font, and the font size in
	points.
	"""
	if font_tuple is None: font_tuple = (None, None, None, None)
	# get the current font and break up the arg
	cur_sz, cur_family, cur_italic, cur_bold = self.font
	set_sz, set_italic, set_bold, set_tt = font_tuple
	# calculate size
	new_sz = self.font_size(font_tuple)
	# calculate variable vs. fixed
	if set_tt:
	    new_family = 'FONTF'
	    self.metric = self.metrics[1]
	else:
	    new_family = 'FONTV'
	    self.metric = self.metrics[0]

	# add modifiers.  Because of the way fonts are named, always
	# add bold modifier before italics modifier, in case both are
	# present
	if set_bold: new_bold = 'B'
	else: new_bold = ''
	if set_italic: new_italic = 'I'
	else: new_italic = ''

	# save the current font specification
	self.font = (new_sz, new_family, new_italic, new_bold)

	# set the font
	font = '%s%s%s' % (new_family, new_bold, new_italic)
	# set the width of a space, an oft used `constant'
	self.space_width = self.text_width(' ')
	return (font, new_sz)

    def text_width(self, text):
	"""Calculate the width of the given text in points using the
	current font size and metrics.
	"""
	if type(self.metric) == type(1.0):
	    return len(text) * self.metric * self.font[0] / 12.0
	else:
	    pointlen = 0.0
	    for c in text: pointlen = pointlen + self.metric[c]
	    cooked = pointlen * self.font_size() / 12.0
	    return cooked * FONT_METRIC_SCALE_FACTOR

    def font_size(self, font_tuple=None):
	if not font_tuple: return self.font[0]
	tuple_sz = font_tuple[0]
	try:
	    if type(tuple_sz) != type(1): return font_sizes[tuple_sz]
	    else: return tuple_sz
	except KeyError: return 12



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
    def __init__(self, psfont, ofile, title=''):
	self.queue = [(START, title)]
	self.font = psfont
	self.ofile = ofile
	self.title = title
	self.curpage = 1
	self.margin = 0

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


    def mark(self): return len(self.queue)

    def pop(self, tagmatch=None):
	try:
	    if not tagmatch or tagmatch == self.queue[-1][0]:
		rtn = self.queue[-1]
		del self.queue[-1]
		return rtn
	    else: return (None, None)
	except IndexError: return (None, None)

    def break_lines(self):
	nq = PSQueue(self.font, self.ofile, self.title)
	xpos = 0.0
	tallest = self.font.font_size()
	in_literal_p = 0
	debug_text = ''
	for tag, info in self.queue:
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
		nq.push_vtab(HR_TOP_MARGIN)
		nq.push_horiz_rule()
		nq.push_vtab(HR_BOT_MARGIN)
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
		in_literal_p = info
		nq.push_literal(info)
	    elif tag == SPACE:
		# spaces at the beginning of the line are thrown away,
		# unless we are in literal text
		if in_literal_p or xpos > 0.0:
		    xpos = xpos + (self.font.space_width * info)
		    nq.push_space(info)
		    debug_text = debug_text + ' '
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
		    debug_text = debug_text + info
		    continue
		# the new text doesn't fit on the line so we can do a
		# simple break of the line if the previous tag we saw
		# was a space, and the current line width is > 3/4 of
		# the page width and the current text is smaller than
		# the page width
		_debug('breaking %s: %f\n' %
		       (debug_text, xpos + self.margin + swidth))
		debug_text = ''
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
	        elif ltag:
		    nq.push_string(info)
	# replace our queue with the collapsed queue
	self.queue = nq.queue

    def write_to_postscript(self):
	"""By this time the queue accurately reflects the layout of the
	page.  in other words, for each tag we see, just generate
	the appropriate postscript calls.
	"""
	# now scan through the queue
	render_cmd = 'S'
	ypos = 0.0
	for tag, info in self.queue:
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
		self.ofile.write('/indentmargin %f D\n' %
				 (info * LEFT_MARGIN))
		self.ofile.write('NL\n')
	    elif tag == LABEL:
		if info is not None:
		    self.ofile.write('gsave NL -%f 0 R\n' % info)
		else:
		    self.ofile.write('grestore\n')
	    elif tag == LITERAL:
		pass
	    elif tag == VERT_TAB:
		if ypos - info < -PAGE_HEIGHT:
		    self._end_page()
		    self._start_page(self.curpage)
		    self.curpage = self.curpage + 1
		    ypos = 0.0
		else:
		    ypos = ypos - info
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
	    print '0 0 M'
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
	    print 'save', 0, -PAGE_HEIGHT - 12, "M"
	    print "FONTVI 12 SF"
	    print "(Page", self.curpage, ") S restore"
	    print "showpage"
	    if not trailer:
		self.curpage = self.curpage + 1
		print '%%Page:', self.curpage, self.curpage
		print '0 0 M'
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

    def send_hor_rule(self):
	self.ps.push_horiz_rule()

    def send_label_data(self, data):
	self.ps.push_label(data)
	self.ps.push_string(data)
	self.ps.push_label(None)

    def send_flowing_data(self, data):
	self.ps.push_literal(0)
	self.write_text(data)

    def send_literal_data(self, data):
	self.ps.push_literal(1)
	self.write_text(data)

    def write_text(self, data):
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
    options = getopt.getopt('')

    try:
	inputfile = sys.argv[1]
	ifile = open(inputfile, 'r')
    except (IOError, IndexError):
	ifile = sys.stdin
    try:
	outputfile = sys.argv[2]
	ofile = open(outputfile, 'w')
    except (IOError, IndexError):
	ofile = sys.stdout

    from htmllib import HTMLParser

    w = PSWriter(ofile, None)
    f = AbstractFormatter(w)
    p = HTMLParser(f)
    p.feed(ifile.read())
    p.close()
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
