#! /usr/local/bin/python

"""HTML to PostScript translator.

This module uses the AbstractWriter class interface defined by Grail
to generate PostScript corresponding to a stream of HTML text.  The
HTMLParser class scans the HTML stream, generating high-level calls to
an AbstractWriter object.  This module defines a class derived from
AbstractWriter, called PSWriter, that supports this high level
interface as appropriate for PostScript generation.
"""

import sys
import os
import string
import StringIO
import regsub
from formatter import *



# debugging
DEFAULT_FONT_SIZE = 10
RECT_DEBUG = 0
DEBUG = 0

def _debug(text):
    if DEBUG:
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
PAGE_HEIGHT = (TOP_MARGIN - 2 * BOT_MARGIN)
PAGE_WIDTH = inch_to_pt(8.5) - LEFT_MARGIN - RIGHT_MARGIN

# horizontal rule spacing, in points
HR_TOP_MARGIN = 8.0
HR_BOT_MARGIN = 8.0 

# distance after a label tag in points
LABEL_TAB = 8.0
TAB_STOP = inch_to_pt(0.5)

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
	if not fonts.has_key(self.vfamily): self.vfamily = 'Helvetica'
	if not fonts.has_key(self.ffamily): self.ffamily = 'Courier'
	vrealname, vreg, vbold, vitalic = fonts[self.vfamily]
	frealname, freg, fbold, fitalic = fonts[self.ffamily]
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
	    modulename = 'PSFont_' + \
			 regsub.gsub('-', '_', self.docfonts[fontnickname])
	    module = __import__(modulename)
	    self.fontobjs[fontnickname] = module.font
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
	self._tallest = 0.0
	self._xpos = 0.0
	self._ypos = 0.0
	self._vtab = 0.0
	self._linedata = StringIO.StringIO()
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
	    # swew out ISO encodings
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

    def push_end(self):
#	print 'push_end'
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
#	print 'push_font_change:', font
	if self._linestr:
	    self.close_string()
	self._tallest = max(self._tallest, self._font.font_size())
	psfontname, size = self._font.set_font(font)
	self._space_width = self._font.text_width(' ')
	self._linedata.write('%s %d SF\n' % (psfontname, size))

    def push_space(self, spaces=1):
#	print 'push_space:', spaces
	# spaces at the beginning of a line are thrown away, unless we
	# are in literal text.
	if self._inliteral_p or self._xpos > 0.0:
	    self._linestr.append(' ' * spaces)
	    self._xpos = self._xpos + self._space_width * spaces

    def push_horiz_rule(self):
#	print 'push_horiz_rule'
	self.close_line()
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print '0 -%f R' % HR_TOP_MARGIN
	    print '%f HR' % PAGE_WIDTH
	    print 'NL'
	    print '0 -%f R' % HR_BOT_MARGIN
	finally:
	    sys.stdout = oldstdout

    def push_margin(self, level):
#	print 'push_margin:', level
	self.close_line()
	distance = level * TAB_STOP
	self._margin = distance
	self._ofp.write('/indentmargin %f D\n' % distance)
	self._ofp.write('NL\n')

    def push_label(self, bullet):
#	print 'push_label:', bullet
	if bullet is not None:
	    distance = self._font.text_width(bullet) + LABEL_TAB
	    self._ofp.write('gsave NL -%f 0 R\n' % distance)
	else:
	    ypos = self._ypos
	    self.close_line()
	    self._ypos = ypos
	    self._ofp.write('grestore\n')

    def push_hard_newline(self, blanklines=1):
#	print 'push_hard_newline:', blanklines
	self.close_line()
	self._ofp.write('NL\n')
	if self._inliteral_p:
	    blanklines = blanklines - 1
	if blanklines > 0:
	    # TBD: should we use self._tallest here?  Doesn't look so
	    # good if we do.
	    vtab = 10.0 * 1.1 * blanklines
	    self._ofp.write('0 -%f R\n' % vtab)
	    self._ypos = self._ypos - vtab

    def push_vtab(self, distance):
#	print 'push_vtab:', self._vtab, '+', distance
	self.close_line()
	self._vtab = self._vtab + distance

    def push_underline(self, flag):
#	print 'push_underline:', flag
	render = flag and 'U' or 'S'
	if self._render <> render:
	    self.close_string()
	self._render = render

    def push_literal(self, flag):
#	print 'push_literal:', flag
        if self._linestr:
	    self.close_string()
	self._inliteral_p = flag

    def push_string(self, data):
#	print 'push_string:', string
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
		elif linestr[-1][-1] in [' ', '\t'] and \
		     xpos + margin > PAGE_WIDTH * 0.75 and \
		     width < PAGE_WIDTH:
		    #
		    # first output the current line data
		    #
		    self.close_line(linestr=linestr)
		    # close_line() touches these, but we're using a
		    # local variable cache, which must be updated.
		    xpos = 0.0
		    linestr = []
		    self._ofp.write('NL\n')
		    linestr.append(word)
		    xpos = xpos + width
		# Try an alternative line break strategy.  If we're
		# closer than 75% of the page width to the end of the
		# line, then start a new line, print the word,
		# possibly splitting the word if it is longer than a
		# single line.
		else:
		    self.close_line(linestr=linestr)
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
			self._ofp.write('NL\n')
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
	    print '0 0 M NL'
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
	    print 'save', 0, PAGE_TAB, "M"
	    print "FONTV 8 SF"
	    print "(", self._url, ") S"
	    print "FONTVI 12 SF"
	    print "(Page", self._pageno, ") EDGE restore"
	    print "showpage"
	finally:
	    sys.stdout = stdout

    def close_line(self, linestr=None):
	if linestr is None: linestr = self._linestr
	if linestr:
	    self.close_string(linestr)
	if self._linedata.tell() > 0:
	    self._ypos = self._ypos - self._vtab
	    # check to see if we're at the end of the page
	    if self._ypos <= -PAGE_HEIGHT:
		self.print_page_postamble()
		self._pageno = self._pageno + 1
		self.print_page_preamble()
		self._ypos = 0.0
	    self._ofp.write('0 -%f R\n' % self._vtab)
	    self._ofp.write(self._linedata.getvalue())
	    self._linedata = StringIO.StringIO()
	    self._xpos = 0.0
	    self._tallest = self._font.font_size()
	    self._vtab = self._tallest

    def close_string(self, linestr=None):
	if linestr is None: linestr = self._linestr
	contiguous = string.joinfields(linestr, '')
	# handle quoted characters
	cooked = regsub.gsub(QUOTE_re, '\\\\\\1', contiguous)
	# TBD: handle ISO encodings
	pass
	self._linedata.write('(%s) %s\n' % (cooked, self._render))
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
	font = PSFont()
	font.set_font((10, 'FONTV', '', ''))
        self.ps = PSStream(font, ofile, title, url)
	self.ps.start()

    def close(self):
#	print 'close'
	self.ps.push_end()

    def new_font(self, font):
#	print 'new_font:', font
	self.ps.push_font_change(font)

    def new_margin(self, margin, level):
#	print 'new_margin:', margin, level
	self.ps.push_margin(level)

    def new_spacing(self, spacing):
#	print "new_spacing(%s)" % `spacing`
	raise RuntimeError

    def new_styles(self, styles):
#	print 'new_styles:', styles
	# semantics of STYLES is a tuple of single char strings.
	# Right now the only styles we support are lower case 'u' for
	# underline.
	if 'u' in styles:
	    self.ps.push_underline(1)
	else:
	    self.ps.push_underline(0)

    def send_paragraph(self, blankline):
#	print 'send_paragraph:', blankline
	self.ps.push_hard_newline(blankline)

    def send_line_break(self):
#	print 'send_line_break'
	self.ps.push_hard_newline()

    def send_hor_rule(self):
#	print 'send_hor_rule'
	self.ps.push_horiz_rule()

    def send_label_data(self, data):
#	print 'send_label_data:', data
	self.ps.push_label(data)
	self.ps.push_string(data)
	self.ps.push_label(None)

    def send_flowing_data(self, data):
#	print 'send_flowing_data:', data
	self.ps.push_literal(0)
	self.ps.push_string(data)

    def send_literal_data(self, data):
#	print 'send_literal_data:', data
	self.ps.push_literal(1)
	self.ps.push_string(data)


def main():
    import getopt
    import os
    help = None
    error = 0
    logfile = None
    try:
	options, argv = getopt.getopt(sys.argv[1:], 'hdl:')
    except getopt.error:
	error = 1
	help = 1
    for opt, arg in options:
	if opt == '-h': help = 1
	elif opt == '-d': DEBUG = 1
	elif opt == 'l': logfile = arg
    if help:
	stdout = sys.stderr
	try:
	    sys.stdout = sys.stderr
	    print 'Usage:', sys.argv[0], '[-h] [-d] [-l logfile] [file]'
	    print '    -h: this help message'
	    print '    -d: turn on debugging'
	    print '    -l: logfile for debugging, otherwise stderr'
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
    infile = argv[0]
    if argv: infp = open(infile, 'r')
    else: infp = sys.stdin
    # create the parsers
    w = PSWriter(sys.stdout, None, url=infile or '')
    f = AbstractFormatter(w)
    # We don't want to be dependent on Grail, but we do want to use it
    # if it's around.  Only current difference is that links are
    # underlined with the PrintDialog parser.
    try:
	import PrintDialog
	p = PrintDialog.PrintingHTMLParser(f)
    except:
	import htmllib
	p = htmllib.HTMLParser(f)
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
/NL {indentmargin currentpoint E pop M} D
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
