"""HTML to PostScript generator.

This module uses the HTMLParser class in the htmllib module as the
front-end parser of HTML 2.0.  It sets itself up as the backend
formatter and generates PostScript instead of rendering HTML on a
screen.
"""

__version__ = "$Id: html2ps.py,v 1.2 1995/09/12 18:54:58 bwarsaw Exp $"

import sys
import string
import StringIO
import regsub
from formatter import *

RECT_DEBUG = 1
DEBUG = 1

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
PS_HEADER_FILE = 'header.ps'
ISO_LATIN1_FILE = 'latin1.ps'
CR = '\015'
LF = '\012'
CRLF_re = '%c\\|%c' % (CR, LF)


# the next page sizes are a compromise between letter sized paper
# (215.9 x 279.4 mm) and european standard A4 sized paper (210.0 x
# 297.0 mm).  Note that PAGE_WIDTH is not the actual width of the
# paper

TOP_MARGIN = (10.5*72)
BOT_MARGIN = (0.5*72)
LEFT_MARGIN = (0.5*72)
RIGHT_MARGIN = LEFT_MARGIN
PAGE_HEIGHT = (TOP_MARGIN - 2 * BOT_MARGIN)
PAGE_WIDTH = (8*72) - LEFT_MARGIN

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
	# get the current font and break up the arg
	cur_sz, cur_family, cur_italic, cur_bold = self.font
	set_sz, set_italic, set_bold, set_tt = font_tuple
	# calculate size
	try:
	    if type(set_sz) != type(1): new_sz = font_sizes[set_sz]
	    else: new_sz = set_sz
	except KeyError: new_sz = 12
	# calculate variable vs. fixed
	if set_tt is AS_IS: new_family = cur_family
	elif set_tt:
	    new_family = 'FONTF'
	    self.metric = self.metrics[1]
	else:
	    new_family = 'FONTV'
	    self.metric = self.metrics[0]

	# add modifiers.  Because of the way fonts are named, always
	# add bold modifier before italics modifier, in case both are
	# present
	if set_bold is AS_IS: new_bold = cur_bold
	elif set_bold: new_bold = 'B'
	else: new_bold = ''
	if set_italic is AS_IS: new_italic = cur_italic
	elif set_italic: new_italic = 'I'
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
#	    _debug('%20s: raw= %f, cooked= %f\n' %
#		   (text, pointlen, cooked))
#           return pointlen * self.font[0] / 12.0
	    return cooked

    def font_size(self):
	return self.font[0]



class PSBuffer:
    """Handles the printing of output to a PostScript buffer.
    Uses an output buffer which has output file semantics
    (i.e. supports a write method and a flush method), and must
    already be opened for writing."""
    def __init__(self, out, varifamily='Helvetica', fixedfamily='Courier'):
	self.obuffer = out
	self.current_page = 0
	# X,Y position on the current PostScript page in points.
	self.current_pos = (0, 0)
	# PostScript font object
	self.font = PSFont(varifamily, fixedfamily)
	# line output buffering
	self.lbuffer = StringIO.StringIO()
	self.lwidth = 0.0
	self.tallest = self.font.font_size()

    def flush(self):
	"""Flush the current line buffer to the output buffer."""
	if self.lbuffer.tell() > 0:
	    self.lbuffer.seek(0)
	    self.obuffer.write(self.lbuffer.read())
	    self.lbuffer = sys.stdout = StringIO.StringIO()
	    self.lwidth = 0.0

    def set_font(self, font_tuple):
	"""Change local font to that specified by FONT_TUPLE, where
	FONT_TUPLE is a 4-tuple of (SIZE, ITALIC, BOLD, TT)
	"""
	postscript_font, font_size = self.font.set_font(font_tuple)
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.lbuffer
	    print postscript_font, font_size, "SF"
	    self.tallest = max(self.tallest, font_size)
	finally:
	    sys.stdout = oldstdout

    def x(self): return self.current_pos[0]
    def y(self): return self.current_pos[1]

    def _moveto(self, x, y):
	"""Move PostScripts current position to (X, Y).  No checking is
	made for that position being visible, nor is page or line breaking
	performed.  If X or Y is None, then the current position is
	substituted for that parameter.  The PostScript commands are not
	buffered.
	"""
	if x is None: x = self.x()
	if y is None: y = self.y()
	self.current_pos = (x, y)
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
	    print x, y, "M"
	finally: sys.stdout = oldstdout

    def _line_break(self, trailer_p=None):
	"""Issue a PostScript line break, flushing the current line
	buffer if necessary, and issuing page break instructions if
	necessary.
	"""
	vert_space = self.tallest * 1.1
	if self.y() - vert_space < -PAGE_HEIGHT:
	    self._page_break(trailer_p)
	self._moveto(0, self.y() - vert_space)
	self.flush()
	self.tallest = self.font.font_size()

    def _page_break(self, trailer_p=None):
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
	    print 'save', 0, -PAGE_HEIGHT - 12, "M"
	    print "FONTVI 12 SF"
	    print "(Page", self.current_page, ") S restore"
	    self.showpage()
	    if not trailer_p: self.newpage()
	finally:
	    sys.stdout = oldstdout
	self._moveto(0, 0)

    def showpage(self):
	"""Show the current page and restore any changes to the printer
	state."""
	self.obuffer.write("showpage\n")

    def newpage(self):
	"""Increment the page count and handle the structured comment
	conventions."""
	self.current_page = self.current_page + 1
	# The PostScript reference Manual states that the Page: Tag
	# should have a label and a ordinal; otherwise programs like
	# psutils fail -gustaf
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
	    print "%%Page:", self.current_page, self.current_page
	    print "save\nNP"
	    if RECT_DEBUG:
		print 0, 0, "M"
		print PAGE_WIDTH, 0, "RL"
		print 0, -PAGE_HEIGHT, "RL"
		print -PAGE_WIDTH, 0, "RL closepath stroke newpath"
	    self._moveto(0, 0)
	finally:
	    sys.stdout = oldstdout
	# restore the font
	self.set_font( (None, None, None, None) )

    def _raw_write(self, word, draw_cmd='S'):
	"""Writes WORD to output buffer sys.stdout.  Handles PostScript
	quoting and ISO encodings.  Also handles line breaking when current
	buffered line exceeds page width.
	"""
	# calculate line widths
	wwidth = self.font.text_width(word)
	# handle quoted characters
	word = regsub.gsub(QUOTE_re, '\\\\\\1', word)
	# TBD: handle ISO encodings
	pass
	# break the line if necessary
	if self.x() + wwidth + self.lwidth > PAGE_WIDTH:
	    self._line_break()
	# now write out the word and trailing space, then re-adjust
	# the buffered line length
	print '(%s ) %s' % (word, draw_cmd)
	self.lwidth = self.lwidth + wwidth + self.font.space_width

    def write_text(self, text, underline_p=None):
	"""Writes a flow of words to the PostScript output buffer.  The
	text written will be rendered in the same style.  Note that
	output is buffered until the line width is filled.  This facilitates
	horizontal as well as vertical positioning of the line.  Hard
	newlines in the text are translated to line breaks, flushing the
	buffer.
	"""
	# note the and/or trick for C's equivalent ?: constructs
	draw_cmd = underline_p and 'U' or 'S'
	# start splitting the text up until it fits on the current
	# line.  We make some assumptions here.  First, the text has
	# already been normalized.  CR/NL's have been collapsed so
	# they are only there if really desired -- we'll put in hard
	# newlines.
	oldstdout = sys.stdout
	try:
	    linecnt = 0
	    sys.stdout = self.lbuffer
	    for line in string.splitfields(text, '\n'):
		# buffer each line of output
		for word in string.splitfields(line, ' '):
		    self._raw_write(word)
		# add hard newlines
		if linecnt > 0: self._line_break()
		linecnt = linecnt + 1
	finally:
	    sys.stdout = oldstdout

    def file_to_buffer(self, filename):
	fp = open(filename, 'r')
	self.obuffer.write(fp.read())
	fp.close()

    def header(self, title=None):
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
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
	    self.file_to_buffer(PS_HEADER_FILE)
	    # define the fonts
	    for docfont in docfonts.keys():
		print "/%s" % docfont, "{/%s}" % docfonts[docfont], "D"

	    # swew out ISO encodings
	    self.file_to_buffer(ISO_LATIN1_FILE)
	    # finish out the prolog
	    print "/xmargin", LEFT_MARGIN, "D"
	    print "/topmargin", TOP_MARGIN, "D"
	    print "/scalfac", self.font.points_per_pixel, "D"
	    print "%%EndProlog"
	finally:
	    sys.stdout = oldstdout
	    
    def trailer(self):
	self._line_break(1)
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
	    print "%%Trailer"
	    print "restore"
	    print "%%Pages:", self.current_page
	finally:
	    sys.stdout = oldstdout

    def ruler(self):
	self._line_break()
	oldstdout = sys.stdout
	try:
	    sys.stdout = self.obuffer
	    print "gsave", 0, self.y(), "M"
	    print PAGE_WIDTH, 0, "RL stroke"
	    for p in range(0, 72 * PAGE_WIDTH, 4.5):
		print p, self.y(), "M"
		ll = ruler[int((p%72) / 4.5)]
		print 0, ll, "RL stroke"
	    print "grestore"
	finally:
	    sys.stdout = oldstdout



class PSWriter(AbstractWriter):
    def __init__(self):
	pass

    def new_font(self, font):
	print "new_font(%s)" % `font`

    def new_margin(self, margin, level):
	print "new_margin(%s, %d)" % (`margin`, level)

    def new_spacing(self, spacing):
	print "new_spacing(%s)" % `spacing`

    def new_styles(self, styles):
	print "new_styles(%s)" % `styles`

    def send_paragraph(self, blankline):
	print "send_paragraph(%s)" % `blankline`

    def send_line_break(self):
	print "send_line_break()"

    def send_hor_rule(self):
	print "send_hor_rule()"

    def send_label_data(self, data):
	print "send_label_data(%s)" % `data`

    def send_flowing_data(self, data):
	print "send_flowing_data(%s)" % `data`

    def send_literal_data(self, data):
	print "send_literal_data(%s)" % `data`



def test_args():
    # set the output file
    try:
	filename = sys.argv[1]
	ofile = open(filename, 'w')
	ps = PSBuffer(ofile)
    except:
	ps = PSBuffer(sys.stdout)

    try: title = sys.argv[2]
    except IndexError: title = None
    ps.header(title)
    return ps

def test():
    ps = test_args()
    ps.newpage()
    ps.set_font((12, 0, 0, 1))
    ps.write_text('Here is a fairly long line of text in fixed width')
    ps.write_text('roman font, 12 point size.  Before I change to a different')
    ps.write_text('font, I would like to say something... "something".')
    ps.write_text('Now changing to')
    ps.set_font((18, 0, 0, 1))
    ps.write_text('18 point font size, but')
    ps.write_text('supercalifragilistic-expiallidocious-anti-disestablishment')
    ps.write_text('keeping the rest of the')
    ps.write_text('characteristics')
    ps.write_text('the same.')
    ps.write_text('Astonishingly enough,')
    ps.write_text('I will now change to')
    ps.set_font((24, 1, 1, 0))
    ps.write_text('24 point, variable width bold italic font,')
    ps.write_text('and is it not compelling how beautiful even')
    ps.write_text('this obliquely slantified font appears to the naked eye?')
    ps.write_text('Why should it look the same as')
    ps.set_font((12, 0, 1, 0))
    ps.write_text('twelve point bold, non-italic (or is that,')
    ps.write_text('non-oblique) font looks?\n\n')
    ps.write_text('Now that I have started a')
    ps.write_text('new paragraph, although not, of course, a new page')
    ps.write_text('I would like to (say) `speak\' a few things that //I//')
    ps.write_text('normally wouldn\'t have been able to.  Although now I am')
    ps.write_text('not starting a')
    ps.set_font((10, 1, 0, 0))
    ps.write_text('new paragraph, I am beginning a different look')
    ps.write_text('to the text that I will be spewing out.  Gosh is this')
    ps.write_text('not super hip?  I sure think it is, so who cares')
    ps.write_text('what you think, eh?')
    ps.write_text('I would actually like to know because, dang it, I am')
    ps.write_text('really friggin close to finishing at least preliminary')
    ps.write_text('PostScript support.  Once the formatting rules are done')
    ps.write_text('then I can begin mapping this stuff to the API required')
    ps.write_text('by Grail.  By and by, it all looks pretty good, however')
    ps.write_text('it does appear as if the smaller than twelve point text,')
    ps.write_text('i.e. the 10 point text you are now looking at,')
    ps.write_text('is not quite calculated correctly... hmmm!')
    ps.trailer()
    

def metrics_test_1():
    ps = test_args()
    ps.newpage()

    # spew some stuff for metrics
    spew = [
	(0, 0, 0, 'Variable Normal'),
	(1, 0, 0, 'Variable Italic'),
	(0, 1, 0, 'Variable Bold'),
	(1, 1, 0, 'Variable Bold Italic'),
	
	(0, 0, 1, 'Fixed Normal'),
	(1, 0, 1, 'Fixed Italic'),
	(0, 1, 1, 'Fixed Bold'),
	(1, 1, 1, 'Fixed Bold Italic')
	]

    for s in spew:
	italic, bold, tt, name = s
	ps.set_font((12, italic, bold, tt))
	ps.write_text(name)
	ps.line_break()
	ps.write_text('M' * 50)
	ps.line_break()
	ps.write_text('.' * 50)
	ps.line_break()

    ps.showpage()
    ps.trailer()


def metrics_test_2():
    ps = test_args()
    ps.newpage()

    for c in range(32, 127):
	for bold in [0, 1]:
	    for italic in [0, 1]:
		ps.set_font((12, bold, italic, 0))
		text = '|' + chr(c) * 40 + '|\n'
		ps.write_text(text)

    ps.trailer()


def metrics_test_3():
    ps = test_args()
    ps.newpage()
    for c in range(32, 127):
	for s in [8, 10, 12, 14, 18, 24]:
	    ps.set_font((s, 0, 0, 0))
	    text = '|' + chr(c) * 10 + '|\n'
	    ps.write_text(text)
	    ps.ruler()

    ps.trailer()
	    


if __name__ == '__main__':
    metrics_test_3()
    #test()
