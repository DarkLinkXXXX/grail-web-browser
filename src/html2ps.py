#! /usr/local/bin/python

"""HTML to PostScript translator.

This module uses the AbstractWriter class interface defined by Grail
to generate PostScript corresponding to a stream of HTML text.  The
HTMLParser class scans the HTML stream, generating high-level calls to
an AbstractWriter object.  This module defines a class derived from
AbstractWriter, called PSWriter, that supports this high level
interface as appropriate for PostScript generation.

Note that this module can be run as a standalone script for command
line conversion of HTML files to PostScript.

"""

import sys
import os

# TBD: We need to do this path munging so we can pick up the proper
# version of ni.py.  The one in the Python 1.3 library has bugs.
if __name__ == '__main__':
    script_dir = os.path.dirname(sys.argv[0])
    script_dir = os.path.join(os.getcwd(), script_dir)
    script_dir = os.path.normpath(script_dir)

    for path in 'pythonlib', script_dir:
	sys.path.insert(0, os.path.join(script_dir, path))


import ni

# standard imports as part of Grail or as standalone
import string
import StringIO
import regsub
from htmllib import HTMLParser
from formatter import AbstractFormatter, AbstractWriter
import fonts



# debugging
DEFAULT_FONT_SIZE = 10
RECT_DEBUG = 0
DEBUG = 1

def _debug(text):
    if DEBUG:
	if text[-1] <> '\n':
	    text = text + '\n'
	sys.stderr.write(text)
	sys.stderr.flush()


# This dictionary maps PostScript font names to the normal, bold and
# italic suffixes for the font.  Key is the short name describing the
# font, value is a tuple indicating the real name of the font (for
# mapping fonts to other fonts), then the regular, bold, and italic
# suffix modifiers of the font.  Note that if their is no regular name
# modifier, then use the empty string, but if there is a regular name
# modifier, make sure it includes a leading dash.  Other modifiers
# should not include the dash.

fontdefs = {
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
    None: DEFAULT_FONT_SIZE,
    'h1': 18,
    'h2': 14,
    'h3': 12,
    'h4': 10,
    'h5': 10,
    'h6': 10
    }



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
LEFT_MARGIN = inch_to_pt(1.0)		# was 0.75
RIGHT_MARGIN = inch_to_pt(1.0)		# was 1.0
PAGE_HEIGHT = (TOP_MARGIN - 2 * BOT_MARGIN) # 648
PAGE_WIDTH = inch_to_pt(8.5) - LEFT_MARGIN - RIGHT_MARGIN

# horizontal rule spacing, in points
HR_TOP_MARGIN = 8.0
HR_BOT_MARGIN = 8.0 
HR_LINE_WIDTH = 1.0

# distance after a label tag in points
LABEL_TAB = 6.0
TAB_STOP = inch_to_pt(0.5)

# page indicator yposition
HEADER_POS = inch_to_pt(0.25)
FOOTER_POS = -PAGE_HEIGHT - inch_to_pt(0.5)

# I don't support color yet
F_FULLCOLOR = 0
F_GREYSCALE = 1
F_BWDITHER = 2
F_REDUCED = 3


def distance(start, end):
    """Returns the distance between two points."""
    if start < 0 and end < 0:
	return abs(min(start, end) - max(start, end))
    elif start >= 0 and end >= 0:
	return max(start, end) - min(start, end)
    else:
	#  one neg, one pos
	return max(start, end) - min(start, end)



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
    """
    def __init__(self, varifamily='Times', fixedfamily='Courier'):
	"""Create a font definition using VARIFAMILY as the variable
	width font and FIXEDFAMILY as the fixed width font.  Defaults
	to Helvetica and Courier respectively.
	"""
	# current font is a tuple of size, family, italic, bold
	self.vfamily = varifamily
	self.ffamily = fixedfamily
	self.font = (DEFAULT_FONT_SIZE, 'FONTV', '', '')

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
	if not fontdefs.has_key(self.vfamily): self.vfamily = 'Helvetica'
	if not fontdefs.has_key(self.ffamily): self.ffamily = 'Courier'
	vrealname, vreg, vbold, vitalic = fontdefs[self.vfamily]
	frealname, freg, fbold, fitalic = fontdefs[self.ffamily]
	# fonts may be mapped to other fonts
	if not vrealname: vrealname = self.vfamily
	if not frealname: frealname = self.ffamily

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
	# instantiated font objects
	self.fontobjs = {}
	self.tw_func = None

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

	if set_italic: new_italic = 'I'
	else: new_italic = ''

	# save the current font specification
	self.font = (new_sz, new_family, new_italic, new_bold)

	# set the font nickname
	fontnickname = '%s%s%s' % (new_family, new_bold, new_italic)

	# make sure the font object is instantiated
	if not self.fontobjs.has_key(fontnickname):
	    psfontname = self.docfonts[fontnickname]
	    self.fontobjs[fontnickname] = fonts.font_from_name(psfontname)
	self.tw_func = self.fontobjs[fontnickname].text_width

	# return the PostScript font definition and the size in points
	return (fontnickname, new_sz)

    def text_width(self, text):
	return self.tw_func(self.font[0], text)

    def font_size(self, font_tuple=None):
	"""Return the size of the current font, or the font defined by
	optional FONT_TUPLE if present."""
	if not font_tuple: return self.font[0]
	tuple_sz = font_tuple[0]
	try:
	    if type(tuple_sz) != type(1): return font_sizes[tuple_sz]
	    else: return tuple_sz
	except KeyError: return DEFAULT_FONT_SIZE



class PSStream:
    def __init__(self, psfont, ofp, title='', url=''):
	self._font = psfont
	self._ofp = ofp
	self._title = title
	self._url = url
	self._pageno = 1
	self._margin = 0.0
	# current line state
	self._space_width = 0.0
	self._linestr = []
	self._baseline = None
	self._descender = 0.0
	self._xpos = 0.0
	self._ypos = 0.0
	self._vtab = 0.0		# extra vertical tab before the line
	self._linefp = StringIO.StringIO()
	self._inliteral_p = None
	self._render = 'S'		# S == normal string, U == underline

    def start(self):
	# print document preamble
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print "%!PS-Adobe-1.0"
	    if self._title:
		# replace all cr/lf's with spaces
		self._title = regsub.gsub(CRLF_re, ' ', self._title)
		print "%%Title:", self._title
	    # output font prolog
	    docfonts = self._font.docfonts
	    print "%%DocumentFonts:",
	    for dfv in docfonts.values(): print dfv,
	    print
	    # spew out the contents of the header PostScript file
	    print header_template
	    # define the fonts
	    for docfont in docfonts.keys():
		print "/%s" % docfont, "{/%s}" % docfonts[docfont], "D"
	    # spew out ISO encodings
	    print iso_template
	    # finish out the prolog
	    print "/xmargin", LEFT_MARGIN, "D"
	    print "/topmargin", TOP_MARGIN, "D"
	    print "/indentmargin", 0.0, "D"
	    print "/pagewidth", PAGE_WIDTH, "D"
	    print "/scalfac", self._font.points_per_pixel, "D"
	    print "%%EndProlog"
	finally:
	    sys.stdout = oldstdout
	self.print_page_preamble()
	self.push_font_change(None)

    def push_eps(self, data, bbox, align = 'bottom'):
	"""Insert encapsulated postscript in stream.

	ALIGN must be one of 'top', 'center', or 'bottom'.
	"""
	if not data: return
	if self._linestr:
	    self.close_string()
	ll_x, ll_y, ur_x, ur_y = bbox
	width = distance(ll_x, ur_x)
	height = distance(ll_y, ur_y)

	#  Determine base scaling factor and dimensions:
	if width > PAGE_WIDTH:
	    scale = (1.0 * PAGE_WIDTH) / width
	else:
	    scale = 1.0
	if (scale * height) > PAGE_HEIGHT:
	    scale = (1.0 * PAGE_HEIGHT) / height
	width = scale * width		# compute the maximum dimensions
	height = scale * height

	align = 'bottom'		# limitation!
	if align == 'center':
	    above_portion = below_portion = 0.5
	elif align == 'bottom':
	    above_portion = 1.0
	    below_portion = 0.0
	else:
	    #  assume align == 'top'   ------  just make it 'center' for now!
	    above_portion = below_portion = 0.5

	if width > PAGE_WIDTH - self._xpos:
	    self.close_line()
	above = above_portion * height
	if self._baseline is None:
	    self._baseline = above
	else:
	    self._baseline = max(self._baseline, above)
	#
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._linefp
	    #  Translate & scale for image origin:
	    print 'gsave currentpoint translate %f dup scale' % scale
	    if ll_x or ll_y:
		#  Have to translate again to make image happy:
		print '%d %d translate' % (-ll_x, -ll_y)
	    print data
	    #  Restore context, move to right of image:
	    print 'grestore', width, '0 R'
	finally:
	    sys.stdout = oldstdout

    def push_end(self):
	self.close_line()
	self.print_page_postamble(1)
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print "%%Trailer"
	    print "restore"
	    print "%%Pages:", self._pageno
	finally:
	    sys.stdout = oldstdout

    def push_font_change(self, font):
	if self._linestr:
	    self.close_string()
	psfontname, size = self._font.set_font(font)
	self._space_width = self._font.text_width(' ')
	self._linefp.write('%s %d SF\n' % (psfontname, size))
	if self._baseline is None:
	    self._baseline = self._font.font_size()
	else:
	    self._baseline = max(self._baseline, self._font.font_size())

    def push_space(self, spaces=1):
	# spaces at the beginning of a line are thrown away, unless we
	# are in literal text.
	if self._inliteral_p or self._xpos > 0.0:
	    self._linestr.append(' ' * spaces)
	    self._xpos = self._xpos + self._space_width * spaces

    def push_horiz_rule(self):
	self.close_line()
	self._baseline = HR_TOP_MARGIN
	self._descender = HR_BOT_MARGIN
	self._linefp.write('%f HR\n' % PAGE_WIDTH)
	self.close_line()
	self._ypos = self._ypos - HR_LINE_WIDTH

    def push_margin(self, level):
	if self._linestr:
	    self.close_string()
	distance = level * TAB_STOP
	self._margin = distance
	self._ofp.write('/indentmargin %f D\n' % distance)
	self._ofp.write('CR\n')

    def push_label(self, bullet):
	if self._linestr:
	    self.close_string()
	distance = self._font.text_width(bullet) + LABEL_TAB
	self._linefp.write('gsave CR -%f 0 R (%s) S grestore\n' %
			   (distance, bullet))

    def push_hard_newline(self, blanklines=1):
	self.close_line()
	if self._inliteral_p:
	    blanklines = blanklines - 1
	if blanklines > 0:
	    vtab = self._font.font_size() * blanklines
## 	    _debug('bl= %d, vtab= %f, self._vtab= %f' %
## 		   (blanklines, vtab, self._vtab))
	    self._vtab = self._vtab + vtab

    def push_underline(self, flag):
	render = flag and 'U' or 'S'
	if self._render <> render and self._linestr:
	    self.close_string()
	self._render = render

    def push_literal(self, flag):
        if self._inliteral_p <> flag and self._linestr:
	    self.close_string()
	self._inliteral_p = flag

    def push_string(self, data):
	lines = string.splitfields(data, '\n')
	linecnt = len(lines)-1
	# local variable cache
	xpos = self._xpos
	margin = self._margin
	linestr = self._linestr
	# outer loop
	for line in lines:
	    words = string.splitfields(line, ' ')
	    wordcnt = len(words)-1
	    for word in words:
		width = self._font.text_width(word)
		# Does the word fit on the current line?
		if xpos + width + margin < PAGE_WIDTH:
		    linestr.append(word)
		    xpos = xpos + width
		# The current line, with the additional text, is too
		# long.  We need to figure out where to break the
		# line.  If the previous text was a space, and the
		# current line width is > 75% of the page width, and
		# the current text is smaller than the page width,
		# then just break the line at the last space.
		elif len(linestr) and len(linestr[-1]) and \
		     linestr[-1][-1] in [' ', '\t'] and \
		     xpos + margin > PAGE_WIDTH * 0.75 and \
		     width < PAGE_WIDTH:
		    #
		    # first output the current line data
		    #
		    self.close_line(linestr=linestr)
##		    self._ofp.write('CR\n')
		    # close_line() touches these, but we're using a
		    # local variable cache, which must be updated.
		    xpos = 0.0
		    linestr = []
		    linestr.append(word)
		    xpos = xpos + width
		# Try an alternative line break strategy.  If we're
		# closer than 75% of the page width to the end of the
		# line, then start a new line, print the word,
		# possibly splitting the word if it is longer than a
		# single line.
		else:
		    self.close_line(linestr=linestr)
##		    self._ofp.write('CR\n')
		    # close_line() touches these, but we're using a
		    # local variable cache, which must be updated.
		    xpos = 0.0
		    linestr = []
		    while width > PAGE_WIDTH:
			# make our best guess as to the longest bit of
			# the word we can write on a line.
			average_charwidth = width / len(word)
			chars_on_line = PAGE_WIDTH / average_charwidth
			front = word[:chars_on_line]
			linestr.append(front + '-')
			self.close_line(linestr=linestr)
			# close_line() touches these, but we're using a
			# local variable cache, which must be updated.
			xpos = 0.0
			linestr = []
##			self._ofp.write('CR\n')
			word = word[chars_on_line:]
			width = self._font.text_width(word)
		    linestr.append(word)
		    xpos = width
		# for every word but the last, put a space after it
		if wordcnt > 0:
		    # inlining push_space() for speed
		    if self._inliteral_p or xpos > 0.0:
			linestr.append(' ')
			xpos = xpos + self._space_width
		wordcnt = wordcnt - 1
	    # for every line but the last, put a hard newline after it
	    if linecnt > 0:
		self._linestr = linestr
		self.push_hard_newline()
		# the close_line() call in push_hard_newline() touches
		# these, but we're using a local variable cache, which
		# must be updated.
		xpos = 0.0
		linestr = []
	    linecnt = linecnt - 1
	# undo effects of local variable cache
	self._xpos = xpos
	self._linestr = linestr

    def print_page_preamble(self):
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    # write the structure page convention
	    print '%%Page:', self._pageno, self._pageno
	    print 'NP'
	    print '0 0 M CR'
	    if RECT_DEBUG:
		print 'gsave', 0, 0, "M"
		print PAGE_WIDTH, 0, "RL"
		print 0, -PAGE_HEIGHT, "RL"
		print -PAGE_WIDTH, 0, "RL closepath stroke newpath"
		print 'grestore'
	finally:
	    sys.stdout = oldstdout

    def print_page_postamble(self, trailer=0):
	stdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print 'save'
	    print "FONTV 8 SF"
	    # print title on top of all but first page
	    if self._pageno > 1:
		print 0, HEADER_POS, "M"
		print "(", self._title, ") S"
	    # print url and page number on all pages
	    print 0, FOOTER_POS, "M"
	    print "(", self._url, ") S"
	    print "FONTVI 12 SF"
	    print "(Page", self._pageno, ") EDGE"
	    print "restore showpage"
	finally:
	    sys.stdout = stdout

    def print_page_break(self):
	# will the line we're about to write fit on the current page?
	linesz = self._baseline + self._descender + self._vtab
##	_debug('ypos= %f, linesz= %f, diff= %f, PH= %f' %
##	       (self._ypos, linesz, (self._ypos - linesz), -PAGE_HEIGHT))
	self._ypos = self._ypos - linesz
	if self._ypos <= -PAGE_HEIGHT:
	    self.print_page_postamble()
	    self._pageno = self._pageno + 1
	    self.print_page_preamble()
	    self._ypos = 0.0
	    self._vtab = 0.0
	
    def close_line(self, linestr=None):
	if linestr is None:
	    linestr = self._linestr
	if self._baseline is None:
	    self._baseline = self._font.font_size()
##	print 'ypos=', self._ypos, 'vtab=', self._vtab, 'linestr:', linestr
	if linestr:
	    self.close_string(linestr)
	# do we need to break the page?
	self.print_page_break()
	distance = -self._baseline - self._vtab
	self._ofp.write('CR 0 %f R\n' % distance)
	self._ofp.write(self._linefp.getvalue())
	if self._descender > 0:
	    self._ofp.write('0 %f R\n' % -self._descender)
	    self._descender = 0.0
	# reset cache
	self._linefp = StringIO.StringIO()
	self._xpos = 0.0
	self._vtab = 0.0
	self._baseline = None

    def close_string(self, linestr=None):
	if linestr is None:
	    linestr = self._linestr
	contiguous = string.joinfields(linestr, '')
	# handle quoted characters
	cooked = regsub.gsub(QUOTE_re, '\\\\\\1', contiguous)
	# TBD: handle ISO encodings
	pass
	self._linefp.write('(%s) %s\n' % (cooked, self._render))
	self._linestr = []


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
    def __init__(self, ofile, title='', url=''):
	if not title:
	    title = url
	font = PSFont()
	font.set_font((10, 'FONTV', '', ''))
        self.ps = PSStream(font, ofile, title, url)
	self.ps.start()

    def close(self):
##	_debug('close')
	self.ps.push_end()

    def new_font(self, font):
##	_debug('new_font: %s' % `font`)
	self.ps.push_font_change(font)

    def new_margin(self, margin, level):
##	_debug('new_margin: margin=%s, level=%s' % (margin, level))
	self.ps.push_margin(level)

    def new_spacing(self, spacing): raise RuntimeError

	# semantics of STYLES is a tuple of single char strings.
	# Right now the only styles we support are lower case 'u' for
	# underline.
    def new_styles(self, styles):
##	_debug('new_styles: %s' % styles)
	self.ps.push_underline('u' in styles)

    def send_paragraph(self, blankline):
##	_debug('send_paragraph: %s' % blankline)
	self.ps.push_hard_newline(blankline)

    def send_line_break(self):
##	_debug('send_line_break')
	self.ps.push_hard_newline()

    def send_hor_rule(self):
##	_debug('send_hor_rule')
	self.ps.push_horiz_rule()

    def send_label_data(self, data):
##	_debug('send_label_data: %s' % data)
	self.ps.push_label(data)

    def send_flowing_data(self, data):
##	_debug('send_flowing_data: %s' % data)
	self.ps.push_literal(0)
	self.ps.push_string(data)

    def send_literal_data(self, data):
##	_debug('send_literal_data: %s' % data)
	self.ps.push_literal(1)
	self.ps.push_string(data)

    def send_eps_data(self, eps_data, bbox, align):
##	_debug('send_eps_data: <epsdata>, ' + `bbox`)
	self.ps.push_eps(eps_data, bbox, align)



#  Exception which should not propogate outside this module.
EPSError = 'html2ps.EPSError'

class PrintingHTMLParser(HTMLParser):

    """Class to override HTMLParser's default methods for anchors and images.

    Image loading is controlled by an option parameter, `image_loader.'  The
    value of this parameter should be a function which resolves a URL to an
    image object.  The image object must provide a single method, write(),
    which takes two string parameters:  the name of a file and the name of
    a file format.  This method will be called with the name of a temporary
    file and the string `ppm', indicating that a Portable PixMap
    representation is required.
    """
    def __init__(self, formatter, verbose=0, baseurl=None, image_loader=None):
	HTMLParser.__init__(self, formatter, verbose)
	self._baseurl = baseurl
	self._image_loader = image_loader
	self._image_cache = {}
	self._anchors = {}
	self._anchor_sequence = []

    def close(self):
	if self._anchors:
	    self._formatAnchorList()
	HTMLParser.close(self)

    def _formatAnchorList(self):
	from urlparse import urljoin
	baseurl = self.base or self._baseurl or ''
	self.formatter.add_hor_rule()
	self.formatter.add_flowing_data('URLs referenced in this document:')
	self.formatter.end_paragraph(1)
	self.formatter.push_margin(1)
	self.formatter.push_font((8, None, None, None))
	acnt = len(self._anchor_sequence)
	count = 1
	for anchor in self._anchor_sequence:
	    anchor = urljoin(baseurl, anchor)
	    self.formatter.add_label_data(('[%d]' % count), -1)
	    self.formatter.add_literal_data(anchor)
	    self.formatter.end_paragraph(1)
	    count = count + 1
	self.formatter.pop_margin()

    def anchor_bgn(self, href, name, type):
	self.anchor = href
	if href:
	    self.formatter.push_style(href and 'u' or None)
	    if not self._anchors.has_key(href):
		self._anchors[href] = len(self._anchor_sequence) + 1
		self._anchor_sequence.append(href)

    def anchor_end(self):
	anchor = self.anchor
	if anchor:
	    self.handle_data('[%d]' % self._anchors[anchor])
	    self.formatter.pop_style()

    def handle_image(self, src, alt, ismap, align, *notused):
	if self._image_loader:
	    from urlparse import urljoin, urlparse
	    imageurl = urljoin(self._baseurl, src)
	    if self._image_cache.has_key(imageurl):
		eps_data, bbox = self._image_cache[imageurl]
	    else:
		try:
		    eps_data, bbox = self.load_image(imageurl)
		except EPSError:
		    self.handle_data(alt)
		    return
		else:
		    self._image_cache[imageurl] = (eps_data, bbox)
	    self.formatter.writer.send_eps_data(eps_data, bbox, align)
	    self.formatter.assert_line_data()
	else:
	    self.handle_data(alt)

    def load_image(self, imageurl):
	"""Load image and return EPS data and bounding box.

	If the conversion from raster data to EPS fails, the EPSError is
	raised.
	"""
	image = self._image_loader(imageurl)
	if not image:
	    raise EPSError, 'Image could not be loaded.'
	from tempfile import mktemp
	ppm_fn = mktemp()
	try:
	    image.write(ppm_fn, 'ppm')
	except:
	    raise EPSError, 'Failed to write image to external file.'
	eps_fn = mktemp()
	os.system('pnmtops -scale 1 -nocenter -noturn %s >%s 2>/dev/null'
		  % (ppm_fn, eps_fn))
	os.unlink(ppm_fn)
	fp = open(eps_fn)
	lines = fp.readlines()
	fp.close()
	os.unlink(eps_fn)
	try:
	    lines.remove('showpage\n')
	except:
	    pass			# o.k. if not found
	bbox = None
	for line in lines:
	    if len(line) > 15 and line[:15] == '%%BoundingBox: ':
		bbox = tuple(map(string.atoi, string.split(line[15:])))
		break
	if not bbox:
	    raise EPSError, 'Bounding box not specified.'
	return (string.joinfields(lines, ''), bbox)



def main():
    import getopt
    import os
    help = None
    error = 0
    logfile = None
    title = ''
    url = ''
    try:
	options, argv = getopt.getopt(sys.argv[1:], 'hdl:u:t:')
    except getopt.error:
	error = 1
	help = 1
    for opt, arg in options:
	if opt == '-h': help = 1
	elif opt == '-d': DEBUG = 1
	elif opt == '-l': logfile = arg
	elif opt == '-t': title = arg
	elif opt == '-u': url = arg
    if help:
	stdout = sys.stderr
	try:
	    sys.stdout = sys.stderr
	    print 'Usage:', sys.argv[0], \
		  '[-u url] [-t title] [-h] [-d] [-l logfile] [file]'
	    print '    -u: URL for footer'
	    print '    -t: title for header'
	    print '    -d: turn on debugging'
	    print '    -l: logfile for debugging, otherwise stderr'
	    print '    -h: this help message'
	    print '[file]: file to convert, otherwise from stdin'
	finally:
	    sys.stdout = stdout
	sys.exit(error)
    # crack open log file if given
    stderr = sys.stderr
    if logfile:
	try: sys.stderr = open(logfile, 'a')
	except IOError: sys.stderr = stderr
    # crack open the input file, or stdin
    if argv:
	infile = argv[0]
	infp = open(infile, 'r')
	outfile = os.path.splitext(infile)[0] + '.ps'
	print 'Outputting PostScript to', outfile
	outfp = open(outfile, 'w')
    else:
	infile = None
	infp = sys.stdin
	outfp = sys.stdout
    # create the parsers
    w = PSWriter(outfp, title or None, url or infile or '')
    f = AbstractFormatter(w)
    p = PrintingHTMLParser(f, baseurl=url)
    p.feed(infp.read())
    p.close()
    w.close()


# PostScript templates
header_template = """
%%Creator: CNRI Grail, HTML2PS.PY by Barry Warsaw
%%   Modified underlining to user 'UnderLineString' from pg. 140 of
%%	POSTSCRIPT BY EXAMPLE, by Henry McGilton and Mary Campione,
%%	pub. by Addison Wesley, 1992.  Mods by Fred Drake.
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
/R {rmoveto} D
/L {lineto} D
/RL {rlineto} D
/CR {indentmargin currentpoint E pop M} D
/SQ {newpath 0 0 M 0 1 L 1 1 L 1 0 L closepath} D
/C {dup stringwidth pop pagewidth exch sub 2 div 0 R S} D
/EDGE {0 currentpoint E pop M dup stringwidth pop pagewidth exch sub 0 R S} D
/U {
  currentfont dup /FontMatrix get E /FontInfo get dup
  /UnderlinePosition get E /UnderlineThickness get
  3 -1 roll dtransform /UnderThick E D /UnderPos E D
  currentpoint pop /Start_x E D S currentpoint /End_y E D /End_x E D
  0 UnderPos R Start_x End_x sub 0 RL currentlinewidth
  UnderThick setlinewidth stroke setlinewidth End_x End_y M
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
/HR {/l E D gsave currentpoint 0 E M pop l 0 RL stroke grestore } D
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
##    import profile
##    profile.run("html_test()", "/tmp/html2ps.prof")
##    import pstats
##    p = pstats.Stats("/tmp/html2ps.prof")
##    oldstdout = sys.stdout
##    try:
##	sys.stdout = sys.stderr
##	p.sort_stats('cumulative').print_stats(25)
##    finally:
##	sys.stdout = oldstdout
    main()
