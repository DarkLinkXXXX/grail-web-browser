#! /usr/bin/env python

# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

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

import os
import sys

# TBD: We need to do this path munging so we can pick up the proper
# version of ni.py.  The one in the Python 1.3 library has bugs.

# Always figure the script_dir; this is used to initialize the module
# (see loading of PostScript templates at the end).
script_name = sys.argv[0]
while 1:
    script_dir = os.path.dirname(script_name)
    if not os.path.islink(script_name):
	break
    script_name = os.path.join(script_dir, os.readlink(script_name))
script_dir = os.path.join(os.getcwd(), script_dir)
script_dir = os.path.normpath(script_dir)

if __name__ == '__main__':
    for path in 'pythonlib', 'utils', 'sgml_lex', script_dir:
	sys.path.insert(0, os.path.join(script_dir, path))

import ni

# standard imports as part of Grail or as standalone
import grailutil
import string
import StringIO
import regsub
import urlparse
from types import StringType, TupleType
from HTMLParser import HTMLParser
from formatter import AbstractFormatter, AbstractWriter, AS_IS
import fonts


# debugging
RECT_DEBUG = 0
DEBUG = 0

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
# Entries in the dictionary are factors used with DEFAULT_FONT_SIZE
# The values used by Mosaic
#DEFAULT_FONT_SIZE = 12.0
#font_sizes = {
#    None: 1.0,
#    'h1': 3.0,
#    'h2': 2.0,
#    'h3': 1.5,
#    'h4': 1.67,
#    'h5': 1.0,
#    'h6': 0.83
#    }

# The values used by Grail
DEFAULT_FONT_SIZE = 10.0
font_sizes = {
    None: 1.0,
    'h1': 1.8,
    'h2': 1.4,
    'h3': 1.2,
    'h4': 1.0,
    'h5': 1.0,
    'h6': 1.0
    }


# Page layout and other contants.  Some of this stuff is carried over
# from HTML-PSformat.c and perhaps no longer relevent

# Regular expressions.
L_PAREN = '('
R_PAREN = ')'
B_SLASH = '\\\\'
QUOTE_re = '\\(%c\\|%c\\|%s\\)' % (L_PAREN, R_PAREN, B_SLASH)

# unit conversions:
def inch_to_pt(inches): return inches * 72.0
def pt_to_inch(points): return points / 72.0

# horizontal rule spacing, in points
HR_TOP_MARGIN = 4.0
HR_BOT_MARGIN = 2.0

# paragraph rendering
PARAGRAPH_SEPARATION = 1.0		# * base-font-size

# distance after a label tag in points
LABEL_TAB = 6.0


class PaperInfo:
    def __init__(self, arg):
	if type(arg) is type(''):
	    arg = paper_sizes[arg]
	paperwidth, paperheight, name = arg
	self.PaperHeight = paperheight	# cannonical
	self.PaperWidth = paperwidth	# cannonical
	self.PaperName = name
	self.Rotation = 0.0
	self.TabStop = inch_to_pt(0.5)
	inch = inch_to_pt(1.0)
	self.set_margins((inch, inch, inch, inch)) # cannonical

    def rotate(self, angle):
	if type(angle) is type(''):
	    angle = paper_rotations[angle]
	if angle % 90.0 != 0:
	    raise ValueError, "Illegal page rotation: "  + `angle`
	self.Rotation = angle = angle % 360.0
	if angle % 180.0:
	    pw, ph = self.PaperWidth, self.PaperHeight
	    self.PaperWidth, self.PaperHeight = ph, pw
	self.__update()

    def set_margins(self, (top, bottom, left, right)):
	self.TopMargin = top
	self.BottomMargin = bottom
	self.LeftMargin = left
	self.RightMargin = right
	self.__update()

    def __update(self):
	# cannonical information has changed;
	# re-compute secondary attributes
	self.ImageWidth = self.PaperWidth \
			  - (self.LeftMargin + self.RightMargin)
	self.ImageHeight = self.PaperHeight \
			   - (self.TopMargin + self.BottomMargin)
	# these are relative to the upper edge of the document image area.
	self.HeaderPos = self.TopMargin / 2.0
	self.FooterPos = -(self.ImageHeight
			   + self.BottomMargin / 2.0)

    def dump(self):
	print "Paper information:"
	print "------------------"
	print "PaperName    =", self.PaperName
	print "Rotation     =", self.Rotation
	print "PaperHeight  =", self.PaperHeight
	print "PaperWidth   =", self.PaperWidth
	print "ImageHeight  =", self.ImageHeight
	print "ImageWidth   =", self.ImageWidth
	print "TopMargin    =", self.TopMargin
	print "BottomMargin =", self.BottomMargin
	print "LeftMargin   =", self.LeftMargin
	print "RightMargin  =", self.RightMargin
	print "HeaderPos    =", self.HeaderPos
	print "FooterPos    =", self.FooterPos


paper_sizes = {
    "letter": (inch_to_pt(8.5), inch_to_pt(11.0)),
    "legal": (inch_to_pt(8.5), inch_to_pt(14.0)),
    "executive": (inch_to_pt(7.5), inch_to_pt(10.0)),
    "tabloid": (inch_to_pt(11.0), inch_to_pt(17.0)),
    "ledger": (inch_to_pt(17.0), inch_to_pt(11.0)),
    "statement": (inch_to_pt(5.5), inch_to_pt(8.5)),
    "a3": (842.0, 1190.0),
    "a4": (595.0, 842.0),
    "a5": (420.0, 595.0),
    "b4": (729.0, 1032.0),
    "b5": (516.0, 729.0),
    "folio": (inch_to_pt(8.5), inch_to_pt(13.0)),
    "quarto": (610.0, 780.0),
    "10x14": (inch_to_pt(10.0), inch_to_pt(14.0)),
    }

for size, (pw, ph) in paper_sizes.items():
    paper_sizes[size] = (pw, ph, size)

paper_rotations = {
    "portrait": 0.0,
    "landscape": 90.0,
    "seascape": -90.0,
    "upside-down": 180.0,
    }


ALIGN_LEFT = 'left'
ALIGN_CENTER = 'center'
ALIGN_RIGHT = 'right'

# I don't support color yet
F_FULLCOLOR = 0
F_GREYSCALE = 1
F_BWDITHER = 2
F_REDUCED = 3

# keep images that come above the ascenders for the current line
# from clobbering the descenders of the line above by allowing the
# font height * PROTECT_DESCENDERS_MULTIPLIER.  This should be a
# reasonable percentage of the font height.
PROTECT_DESCENDERS_MULTIPLIER = 0.20


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
    by PostScript functions defined in header.ps.

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
    def __init__(self, varifamily='Times', fixedfamily='Courier',
		 size=DEFAULT_FONT_SIZE):
	"""Create a font definition using VARIFAMILY as the variable
	width font and FIXEDFAMILY as the fixed width font.  Defaults
	to Helvetica and Courier respectively.
	"""
	# current font is a tuple of size, family, italic, bold
	self.vfamily = varifamily
	self.ffamily = fixedfamily
	self.font = (size, 'FONTV', '', '')
	self.base_size = size

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
	# bold-italic version, `B' *must* preceed `I'.  See header.ps
	# for more info.
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

    def get_font(self):
	"""Returns the font nickname and size.

	This is the only place the nickname is computed.
	"""
	sz, family, italic, bold = self.font
	nick = "%s%s%s" % (family, bold, italic)
	return nick, sz

    def set_font(self, font_tuple):
	"""Set the current font to that specified by FONT_TUPLE, which
	is of the form (SIZE, ITALIC?, BOLD?, TT?).  Returns the
	PostScript layer name of the font, and the font size in
	points.  """
	# we *said* we wanted a tuple
	if font_tuple is None: font_tuple = (None, None, None, None)
	set_sz, set_italic, set_bold, set_tt = font_tuple
	# get the current font and break up the tuple
	cur_sz, cur_family, cur_italic, cur_bold = self.font
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

	# get the font nickname
	fontnickname, new_sz = self.get_font()

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
	    if type(tuple_sz) is type(1.0):
		return tuple_sz
	    return font_sizes[tuple_sz] * self.base_size
	except KeyError: return self.base_size


class EPSImage:
    __xscale = 1.0
    __yscale = 1.0

    def __init__(self, data, bbox):
	self.data = data
	self.bbox = bbox
	ll_x, ll_y, ur_x, ur_y = bbox
	self.__width = distance(ll_x, ur_x)
	self.__height = distance(ll_y, ur_y)

    def set_maxsize(self, xmax, ymax):
	"""Scale the image to fit within xmax by ymax points.

	The resulting scale factor may be equal to or less than the
	current scale, but will be no larger.
	"""
	scale = min(self.__xscale, self.__yscale)
	self.set_size(xmax, ymax)
	scale = min(scale, self.__xscale, self.__yscale)
	self.__xscale = self.__yscale = scale

    def set_size(self, xmax, ymax):
	"""Scale image to be as large as possible within xmax by ymax points.

	The resulting scale factor may be greater than 1.0.
	"""
	scale = (1.0 * xmax) / self.__width
	if (scale * self.__height) > ymax:
	    scale = (1.0 * ymax) / self.__height
	self.__xscale = self.__yscale = scale

    def set_scale(self, xscale=1.0, yscale=None):
	"""Set the scaling factor."""
	if yscale is None:
	    yscale = xscale
	self.__xscale = 1.0 * xscale
	self.__yscale = 1.0 * yscale

    def height(self):
	return self.__height * self.__yscale

    def width(self):
	return self.__width * self.__xscale

    def get_scale(self):
	return self.__xscale, self.__yscale

    def xscale(self):
	"""Returns the current horizontal scale factor."""
	return self.__xscale

    def yscale(self):
	"""Returns the current vertical scale factor."""
	return self.__yscale


def cook(string):
    return regsub.gsub(QUOTE_re, '\\\\\\1', string)


class PSStream:
    _pageno = 1
    _margin = 0.0
    _rmargin = 0.0
    _leading = 0.0			# "external" leading == between lines
    _align = ALIGN_LEFT
    _inliteral_p = None
    _render = 'S'			# S == normal string, U == underline
    _prev_render = _render

    # current line state
    _space_width = 0.0
    _baseline = None
    _descender = 0.0
    _xpos = 0.0
    _ypos = 0.0
    _vtab = _leading			# extra vertical tab before the line
    _lineshift = 0.0			# adjustment at start of line

    def __init__(self, psfont, ofp, title='', url='', paper=None):
	self._paper = paper or PaperInfo("letter")
	self._font = psfont
	self._base_font_size = psfont.font_size()
	self._ofp = ofp
	self.set_title(title)
	# strip any fragment identifiers from the url, and pre-cook:
	parsed = urlparse.urlparse(url)
	self._url_cooked = cook(urlparse.urlunparse(parsed[:-1] + ('',)))
	# current line state
	self._linestr = []
	self._yshift = [(0.0, 0.0)]	# vertical baseline shift w/in line
	self._linefp = StringIO.StringIO()

    _title_list = None
    def set_title(self, title):
	# replace all whitespace sequences with a single space
	title = string.join(string.split(title))
	if self._title_list is None:
	    self._title_list = [title]
	else:
	    self._title_list.append(title)

    def get_title(self):
	return self._title_list[0]

    def prune_titles(self):
	del self._title_list[:-1]

    def start(self):
	# print document preamble
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print "%!PS-Adobe-1.0"
	    if self.get_title():
		print "%%Title:", self.get_title()
	    # output font prolog
	    print "%%DocumentPaperSizes:", self._paper.PaperName
	    print "%%DocumentFonts: Symbol ZapfDingbats",
	    docfonts = self._font.docfonts
	    for dfv in docfonts.values(): print dfv,
	    print
	    # spew out the contents of the header PostScript file
	    print standard_header_template
	    # define the fonts
	    print "/scalfac", self._font.points_per_pixel, "D"
	    for docfont in docfonts.keys():
		print "/%s /%s dup reencodeISO D findfont D" \
		      % (docfont, docfonts[docfont])
	    # finish out the prolog with paper information:
	    for name, value in vars(self._paper).items():
		if type(value) is type(''):
		    print "/Gr%s (%s) D" % (name, value)
		else:
		    print "/Gr%s %s D" % (name, value)
	    # Add time information to allow the printing functions to include
	    # 'date printed' to the footers if desired.  We need a way to get
	    # the last-modified time of the document from the context headers,
	    # but these are not available to us at this point.
	    print "%%\n%% time values for use by page decorating functions:"
	    import time
	    names = ("Year", "Month", "Day", "Hour", "Minute", "Second",
		     "Weekday", "Julian", "DST")
	    t = time.time()
	    local = time.localtime(t)
	    utc = time.gmtime(t)
	    for name, local, utc in map(None, names, local, utc):
		print "/Gr%s %s D /GrUTC%s %s D" % (name, local, name, utc)
	    # add per-user customization:
	    user_template, filename = get_userheader()
	    if user_template:
		print "%%\n%% This is custom header material loaded from"
		print "%%", filename
		print user_template
	    print "%%EndProlog"
	finally:
	    sys.stdout = oldstdout
	self.print_page_preamble()
	self.push_font_change(None)	# ???

    def get_pageheight(self):
	return self._paper.ImageHeight

    def get_pagewidth(self):
	return self._paper.ImageWidth - self._margin - self._rmargin

    def set_leading(self, value):
	# `value' is the "internal" leading: for '10 on 12', pass in 12;
	# the stored value is the "external" leading.  This is only computed
	# here.  The external leading is restricted to non-negative values
	# to ensure at least some level of sanity.
	self._leading = max(0.0, value - self._base_font_size)

    def push_eps(self, img, align=None):
	"""Insert encapsulated postscript in stream.
	"""
	if self._linestr:
	    self.close_string()
	if align not in ('absmiddle', 'baseline', 'middle', 'texttop', 'top'):
	    align = 'bottom'

	# Determine base scaling factor and dimensions:
	pagewidth = self.get_pagewidth()
	img.set_maxsize(pagewidth, self.get_pageheight())

	extra = PROTECT_DESCENDERS_MULTIPLIER * self._font.font_size()
	above_portion, below_portion, vshift = 0.5, 0.5, 0.0
	if align == 'absmiddle':
	    vshift = self._font.font_size() / 2.0
	elif align in ('bottom', 'baseline'):
	    above_portion, below_portion = 1.0, 0.0
	elif align != 'middle':
	    # ALIGN == 'top' || ALIGN == 'texttop'
	    above_portion, below_portion, extra = 0.0, 1.0, 0.0
	    vshift = self._font.font_size()

	height = img.height()
	width = img.width()
	above = above_portion * height
	below = (below_portion * height) - vshift

	# Check space available:
	if width > pagewidth - self._xpos:
	    self.close_line()
	# Update page availability info:
	if self._baseline is None:
	    self._baseline = above + self._yshift[-1][0] + vshift + extra
	else:
	    self._baseline = max(self._baseline,
				 above + self._yshift[-1][0] + vshift + extra)
	self._descender = max(self._descender, below - self._yshift[-1][0])
	self._xpos = self._xpos + width
	ll_x, ll_y, ur_x, ur_y = img.bbox
	#
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._linefp
	    #  Translate & scale for image origin:
	    print 'gsave\n currentpoint %s sub translate %s %s scale' \
		  % (below, img.xscale(), img.yscale())
	    if ll_x or ll_y:
		#  Have to translate again to make image happy:
		print ' %d %d translate' % (-ll_x, -ll_y)
	    print img.data
	    #  Restore context, move to right of image:
	    print 'grestore', width, '0 R'
	finally:
	    sys.stdout = oldstdout

    def push_font_string(self, s, font):
	if not font:
	    self.push_string(s)
	    return
	if self._linestr:
	    self.close_string()
	if not self._font.fontobjs.has_key(font):
	    self._font.fontobjs[font] = fonts.font_from_name(font)
	fontobj = self._font.fontobjs[font]
	size = self._font.font_size()
	width = fontobj.text_width(size, s)
	if self._xpos + width > self.get_pagewidth():
	    self.close_line()
	if self._baseline is None:
	    self._baseline = size
	else:
	    self._baseline = max(self._baseline, size)
	self._linefp.write('gsave\n /%s findfont %d scalefont setfont '
			   % (font, size))
	self._linefp.write('(%s) show\ngrestore %d 0 R\n' % (cook(s), width))
	self._xpos = self._xpos + width

    def push_alignment(self, align):
	if align == 'right':
	    self._align = ALIGN_RIGHT
	elif align == 'center':
	    self._align = ALIGN_CENTER
	else:
	    self._align = ALIGN_LEFT

    def push_yshift(self, yshift):
	"""Adjust the current baseline relative to the real baseline.

	The `yshift' parameter is a float value specifying the adjustment
	relative to the current virtual baseline.  Use pop_yshift() to
	undo the effects of the adjustment.
	"""
	if self._linestr:
	    self.close_string()
	yshift = 1.0 * yshift
	self._linefp.write('0 %s R\n' % yshift)
	absshift = self._yshift[-1][0] + yshift
	self._yshift.append((absshift, yshift))
	newheight = absshift + self._font.font_size()
	if self._baseline is None:
	    self._baseline = max(0.0, newheight)
	else:
	    self._baseline = max(self._baseline, newheight)
	if absshift < 0.0:
	    if self._descender is None:
		self._descender = -absshift
	    else:
		self._descender = max(self._descender, -absshift)

    def pop_yshift(self):
	if self._linestr:
	    self.close_string()
	self._linefp.write('0 %s R\n' % -self._yshift[-1][1])
	del self._yshift[-1]

    def push_end(self):
	self.close_line()
	self.print_page_postamble()
	oldstdout = sys.stdout
	try:
	    sys.stdout = self._ofp
	    print "%%Trailer"
	    print "%%Pages:", self._pageno
	    print "%%EOF"
	finally:
	    sys.stdout = oldstdout

    def push_font_change(self, font):
	if self._linestr:
	    self.close_string()
	if self._baseline is None and self._xpos != 0.0:
	    self._baseline = self._font.font_size() \
			     + max(0.0, self._yshift[-1][0])
	psfontname, size = self._font.set_font(font)
	self._linefp.write('%s %s SF\n' % (psfontname, size))
	self._space_width = self._font.text_width(' ')
	newfontsize = self._font.font_size() + max(0.0, self._yshift[-1][0])
	if self._baseline is None:
	    self._baseline = newfontsize
	else:
	    self._baseline = max(self._baseline, newfontsize)

    def push_space(self, spaces=1):
	# spaces at the beginning of a line are thrown away, unless we
	# are in literal text.
	if self._inliteral_p or self._xpos > 0.0:
	    self._linestr.append(' ' * spaces)
	    self._xpos = self._xpos + self._space_width * spaces

    def push_horiz_rule(self, abswidth=None, percentwidth=None,
			height=None, align=None):
	if type(height) is type(0):
	    height = 0.5 * max(height, 1)	# each unit is 0.5pts
	else:
	    height = 1				# 2 "units"
	old_align = self._align
	if align is not None:
	    self.push_alignment(align)
	self._baseline = HR_TOP_MARGIN + height
	descent = PROTECT_DESCENDERS_MULTIPLIER * self._font.font_size()
	self._vtab = max(self._vtab, descent)
	self._descender = HR_BOT_MARGIN
	pagewidth = self.get_pagewidth()
	if abswidth:
	    width = min(1.0 * abswidth, pagewidth)
	elif percentwidth:
	    width = min(1.0, percentwidth) * pagewidth
	else:
	    width = pagewidth
	if self._align is ALIGN_LEFT:
	    start = 0.0
	elif self._align is ALIGN_CENTER:
	    start = (pagewidth - width) / 2
	else:	#  ALIGN = right
	    start = pagewidth - width
	self._linefp.write('%d %s %s HR\n'
			   % (height, start + self._margin, width))
	self.close_line()
	self._align = old_align

    def push_margin(self, level):
	if self._linestr:
	    self.close_string()
	distance = level * self._paper.TabStop
	if self._margin != distance:
	    self._margin = distance
	    self._ofp.write('/grIndentMargin %s D CR\n' % distance)

    def push_rightmargin(self, level):
	if self._linestr:
	    self.close_string()
	self._rmargin = level * self._paper.TabStop

    def push_paragraph(self, blankline):
	if blankline and self._ypos:
	    self._vtab = self._vtab \
			 + (self._base_font_size * PARAGRAPH_SEPARATION)

    def push_label(self, bullet):
	if self._linestr:
	    self.close_string()
	if type(bullet) is StringType:
	    #  Simple textual bullet:
	    distance = self._font.text_width(bullet) + LABEL_TAB
	    cooked = cook(bullet)
	    self._linefp.write('gsave CR -%s 0 R (%s) S grestore\n' %
			       (distance, cooked))
	elif type(bullet) is TupleType:
	    #  Font-based dingbats:
	    string, font = bullet
	    cooked = cook(string)
	    self._linefp.write('gsave\n CR %s %d SF\n'
			       % (font, self._font.font_size()))
	    self._linefp.write(' (%s) dup\n' % cooked)
	    self._linefp.write(' stringwidth pop -%s E sub 0 R S\ngrestore\n'
			       % LABEL_TAB)
	else:
	    #  This had better be an EPSImage object!
	    max_width = self._paper.TabStop - LABEL_TAB
	    bullet.set_scale()
	    bullet.set_maxsize(max_width, self._font.font_size())
	    width = bullet.width()
	    height = bullet.height()
	    distance = width + LABEL_TAB
	    #  Locate new origin:
	    vshift = (self._font.font_size() - height) / 2.0
	    self._linefp.write("gsave\n CR -%s %s R currentpoint translate "
			       "%s %s scale\n"
			       % (distance, vshift,
				  bullet.xscale(), bullet.yscale()))
	    ll_x, ll_y, ur_x, ur_y = bullet.bbox
	    if ll_x or ll_y:
		#  Have to translate again to make image happy:
		self._linefp.write(' %d %d translate\n' % (-ll_x, -ll_y))
	    self._linefp.write(bullet.data)
	    self._linefp.write("grestore\n")

    def push_hard_newline(self, blanklines=1):
	self.close_line()

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
	linestr = self._linestr
	append = linestr.append
	text_width = self._font.text_width
	allowed_width = self.get_pagewidth()
	# outer loop
	for line in lines:
	    # do flowing text
	    words = string.splitfields(line, ' ')
	    wordcnt = len(words)-1
	    for word, width in map(None, words, map(text_width, words)):
		# Does the word fit on the current line?
		if xpos + width < allowed_width:
		    append(word)
		    xpos = xpos + width
		# The current line, with the additional text, is too
		# long.  We need to figure out where to break the
		# line.  If the previous text was a space, and the
		# current line width is > 75% of the page width, and
		# the current text is smaller than the page width,
		# then just break the line at the last space.
		# (Checking the last whitespace char against a tab is
		# unnecessary; data is de-tabbed before this method is
		# called.)
		elif linestr and linestr[-1] and \
		     linestr[-1][-1] == ' ' and \
		     xpos > allowed_width * 0.75 and \
		     width < allowed_width:
		    #
		    # output the current line data (removes trailing space)
		    #
		    linestr[-1] = linestr[-1][:-1]
		    self._xpos = xpos - self._space_width
		    self.close_line(linestr=linestr)
		    # close_line() touches these, but we're using a
		    # local variable cache, which must be updated.
		    xpos = width
		    linestr = [word]
		    append = linestr.append
		# Try an alternative line break strategy.  If we're
		# closer than 75% of the page width to the end of the
		# line, then start a new line, print the word,
		# possibly splitting the word if it is longer than a
		# single line.
		else:
		    self._xpos = xpos
		    self.close_line(linestr=linestr)
		    # close_line() touches these, but we're using a
		    # local variable cache, which must be updated.
		    xpos = 0.0
		    linestr = []
		    append = linestr.append
		    while width > allowed_width:
			# make our best guess as to the longest bit of
			# the word we can write on a line.
			if self._inliteral_p:
			    append(word)
			    word = ''
			    self._xpos = text_width(word)
			else:
			    average_charwidth = width / len(word)
			    chars_on_line = int(allowed_width
						/ average_charwidth)
			    s = word[:chars_on_line]
			    if s[-1] in string.letters:
				s = s + "-"
			    append(s)
			    self._xpos = text_width(s)
			    word = word[chars_on_line:]
			# now write the word
			self.close_line(linestr=linestr)
			# close_line() touches these, but we're using a
			# local variable cache, which must be updated.
			xpos = 0.0
			linestr = []
			append = linestr.append
			width = text_width(word)
		    append(word)
		    xpos = width
		# for every word but the last, put a space after it
		# inlining push_space() for speed
		if wordcnt > 0 and (self._inliteral_p or xpos > 0.0):
		    append(' ')
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
		append = linestr.append
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
	    print '%%BeginPageProlog'
	    psfontname, size = self._font.get_font()
	    print "save", self._margin, psfontname, size, self._pageno, "NP"
	    print '%%EndPageProlog'
	    if RECT_DEBUG:
		print 'gsave', 0, 0, "M"
		print self._paper.ImageWidth, 0, "RL"
		print 0, -self._paper.ImageHeight, "RL"
		print -self._paper.ImageWidth, 0, "RL closepath stroke newpath"
		print 'grestore'
	finally:
	    sys.stdout = oldstdout

    def print_page_postamble(self):
	title = ''
	url = self._url_cooked
	if self._pageno != 1:
	    title = cook(self.get_title())
	self.prune_titles()
	stdout = sys.stdout
	self._ofp.write("(%s)\n(%s)\n%d EP\n" % (url, title, self._pageno))

    def print_page_break(self):
	# will the line we're about to write fit on the current page?
	linesz = self._baseline + self._descender + self._vtab
## 	_debug('ypos= %f, linesz= %f, diff= %f, PH= %f' %
## 	       (self._ypos, linesz, (self._ypos - linesz),
## 		-self._paper.ImageHeight))
	self._ypos = self._ypos - linesz
	if (self._ypos - linesz) <= -self._paper.ImageHeight:
	    self.push_page_break()

    def push_page_break(self):
	# self._baseline could be None
	linesz = (self._baseline or 0.0) + self._descender + self._vtab
	self._ypos = self._ypos - linesz
	self.print_page_postamble()
	self._pageno = self._pageno + 1
	self.print_page_preamble()
	self._ypos = -linesz
	self._vtab = self._leading

    def close_line(self, linestr=None):
	if linestr is None:
	    linestr = self._linestr
	if linestr:
	    self.close_string(linestr)
	baseline = self._baseline
	yshift = self._yshift[-1][0]
	if baseline is None:
	    baseline = self._font.font_size() + max(yshift, 0.0)
	    self._baseline = baseline
	if not self._linefp.getvalue():
	    if self._ypos:
		self._vtab = self._vtab + baseline
	    return
	# do we need to break the page?
	self.print_page_break()
	distance = baseline + self._vtab
	if self._align == ALIGN_CENTER:
	    offset = (self.get_pagewidth() - self._xpos) / 2
	elif self._align == ALIGN_RIGHT:
	    offset = self.get_pagewidth() - self._xpos
	else:
	    offset = 0.0
	self._ofp.write('CR %s -%s R\n%s' %
			(offset, distance, self._linefp.getvalue()))
	if self._descender > 0:
	    self._ofp.write('0 -%s R\n' % self._descender)
	    self._descender = 0.0
	# reset cache
	self._linefp = StringIO.StringIO()
	self._lineshift = yshift
	self._xpos = 0.0
	self._vtab = self._leading
	self._baseline = None

    def close_string(self, linestr=None):
	if linestr is None:
	    linestr = self._linestr
	contiguous = string.joinfields(linestr, '')
	# handle quoted characters
	cooked = cook(contiguous)
	# TBD: handle ISO encodings
	#pass
	render = self._render
	# This only works if 'S' and 'U' are the only values for render:
	if self._prev_render != render and cooked[0] == ' ':
	    cooked = cooked[1:]
	    self._linefp.write('( ) S\n')
	self._linefp.write('(%s) %s\n' % (cooked, render))
	self._prev_render = render
	self._linestr = []


class PSWriter(AbstractWriter):
    """Class PSWriter supports the backend interface expected by
    Grail, actually the HTMLParser class.  It does this by deriving
    from AbstractWriter and overriding methods to interface with the
    PSStream class, which performs the real PostScript work.

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
    _detab_pos = 0

    def __init__(self, ofile, title='', url='',
		 varifamily='Times', fixedfamily='Courier', paper=None,
		 fontsize=None, leading=None):
	if not title:
	    title = url
	font = PSFont(varifamily=varifamily, fixedfamily=fixedfamily,
		      size=fontsize)
	self.ps = PSStream(font, ofile, title, url, paper=paper)
	if leading:
	    self.ps.set_leading(leading)
	self.ps.start()

    def close(self):
##	_debug('close')
	self.ps.push_end()

    def new_alignment(self, align):
##	_debug('new_alignment: %s' % `align`)
	self.ps.push_alignment(align)

    def new_font(self, font):
##	_debug('new_font: %s' % `font`)
	self.ps.push_font_change(font)

    def new_margin(self, margin, level):
##	_debug('new_margin: margin=%s, level=%s' % (margin, level))
	self.ps.push_margin(level)
	self._detab_pos = 0

    def new_spacing(self, spacing):
	raise RuntimeError, 'not yet implemented'

	# semantics of STYLES is a tuple of single char strings.
	# Right now the only styles we support are lower case 'underline' for
	# underline and a 'blockquote' for each right-hand indentation.
    def new_styles(self, styles):
##	_debug('new_styles: %s' % styles)
	self.ps.push_underline('underline' in styles)
	self.ps.push_rightmargin(map(None, styles).count('blockquote'))

    def send_paragraph(self, blankline):
##	_debug('send_paragraph: %s' % blankline)
	self.ps.push_paragraph(blankline)
	self._detab_pos = 0

    def send_line_break(self):
##	_debug('send_line_break')
	self.ps.push_hard_newline()
	self._detab_pos = 0

    def send_hor_rule(self, abswidth=None, percentwidth=None,
		      height=None, align=None):
##	_debug('send_hor_rule')
	self.ps.push_horiz_rule(abswidth, percentwidth, height, align)
	self._detab_pos = 0

    def send_label_data(self, data):
##	_debug('send_label_data: %s' % data)
	self.ps.push_label(data)
	self._detab_pos = 0

    def send_flowing_data(self, data):
##	_debug('send_flowing_data: %s' % data)
	self.ps.push_literal(0)
	self.ps.push_string(data)
	self._detab_pos = 0

    def send_literal_data(self, data):
##	_debug('send_literal_data: %s' % data)
	self.ps.push_literal(1)
	self.ps.push_string(self._detab_data(data))

    def send_eps_data(self, image, align):
##	_debug('send_eps_data: <epsdata>, ' + `bbox`)
	self.ps.push_eps(image, align)
	self._detab_pos = 0

    def _detab_data(self, data):
	pos = self._detab_pos
	s = []
	append = s.append
	for c in data:
	    if c == '\n':
		append('\n')
		pos = 0
	    elif c == '\t':
		append(' ' * (8 - (pos % 8)))
		pos = 0
	    else:
		append(c)
		pos = pos + 1
	self._detab_pos = pos
	return string.joinfields(s, '')


#  Exception which should not propogate outside this module.
EPSError = "html2ps.EPSError"


#  Dictionary of image converters from key ==> EPS.
#  The values need to be formatted against a dictionary that contains the
#  values `i' for the input filename and `o' for the output filename.
image_converters = {
    ('gif', 'color') : 'giftopnm %(i)s | pnmtops -noturn >%(o)s',
    ('gif', 'grey') : 'giftopnm %(i)s | ppmtopgm | pnmtops -noturn >%(o)s',
    ('jpeg', 'color') : 'djpeg -pnm %(i)s | pnmtops -noturn >%(o)s',
    ('jpeg', 'grey') : 'djpeg -grayscale -pnm %(i)s | pnmtops -noturn >%(o)s',
    ('pbm', 'grey') : 'pbmtoepsi %(i)s >%(o)s',
    ('pgm', 'grey') : 'pnmtops -noturn %(i)s >%(o)s',
    ('ppm', 'color') : 'pnmtops -noturn %(i)s >%(o)s',
    ('ppm', 'grey') : 'ppmtopgm %(i)s | pnmtops -noturn >%(o)s',
    ('rast', 'color') : 'rasttopnm %(i)s | pnmtops -noturn >%(o)s',
    ('rast', 'grey') : 'rasttopnm %(i)s | ppmtopgm | pnmtops -noturn >%(o)s',
    ('rgb', 'color') : 'rgb3toppm %(i)s | pnmtops -noturn >%(o)s',
    ('rgb', 'grey') : 'rgb3toppm %(i)s | ppmtopgm | pnmtops -noturn >%(o)s',
    ('tiff', 'color') : 'tifftopnm %(i)s | pnmtops -noturn >%(o)s',
    ('tiff', 'grey') : 'tifftopnm %(i)s | ppmtopgm | pnmtops -noturn >%(o)s',
    ('xbm', 'grey') : 'xbmtopbm %(i)s | pbmtoepsi >%(o)s',
    ('xpm', 'color') : 'xpmtoppm %(i)s | pnmtops -noturn >%(o)s',
    ('xpm', 'grey') : 'xpmtoppm %(i)s | ppmtopgm | pnmtops -noturn >%(o)s'
    }


class PrintingHTMLParser(HTMLParser):

    """Class to override HTMLParser's default methods.

    Special support is provided for anchors, BASE, images, subscripts,
    and superscripts.

    Image loading is controlled by an optional parameter called
    `image_loader.'  The value of this parameter should be a function
    which resolves a URL to raw image data.  The image data should be
    returned as a string.

    If an image loader is provided, the `greyscale' parameter is used
    to determine how the image should be converted to postscript.

    The interpretation of anchor tags is controlled by two options,
    `footnote_anchors' and `underline_anchors.'  If footnote_anchors
    is true, anchors are assigned footnote numbers and the target URL
    is printed in a list appended following the body of the document.
    The underline_anchors flag controls the visual treatment of the
    anchor text in the main document.
    """
    iconpath = []
    _inited = 0

    def __init__(self, writer, verbose=0, baseurl=None, image_loader=None,
		 greyscale=1, underline_anchors=1):
	if not self._inited:
	    for k, v in self.fontdingbats.items():
		self.dingbats[(k, 'grey')] = v
		self.dingbats[(k, 'color')] = v
	    from ancillary import Greek
	    for k, v in Greek.entitydefs.items():
		tup = (v, 'Symbol')
		self.dingbats[(k, 'grey')] = tup
		self.dingbats[(k, 'color')] = tup
	    PrintingHTMLParser._inited = 1
	from formatter import AbstractFormatter
	HTMLParser.__init__(self, AbstractFormatter(writer), verbose)
	self._baseurl = baseurl
	self._greyscale = greyscale
	self._image_loader = image_loader
	self._image_cache = {}
	self._underline_anchors = underline_anchors
	self._anchors = {None: None}
	self._anchor_sequence = []
	self._anchor_xforms = []

    def close(self):
	HTMLParser.close(self)
	if self._anchor_sequence:
	    self._formatAnchorList()

    def add_anchor_transform(self, xform):
	if xform not in self._anchor_xforms:
	    self._anchor_xforms.append(xform)

    def remove_anchor_transform(self, xform):
	if xform in self._anchor_xforms:
	    self._anchor_xforms.remove(xform)

    def do_base(self, attrs):
	HTMLParser.do_base(self, attrs)
	if self.base and not self._baseurl:
	    self.formatter.writer.ps._url = self.base

    def _footnote_anchor(self, href, attrs):
	if self._anchor_xforms:
	    for xform in self._anchor_xforms:
		href = xform(href, attrs)
		if not href:
		    return None
		attrs['href'] = href
	else:
	    href = disallow_data_scheme(href, attrs)
	return href

    def _formatAnchorList(self):
	baseurl = self.base or self._baseurl or ''
	self.close_paragraph()
	self.formatter.end_paragraph(1)
	self.do_hr({})
	self.start_p({'align':'left'})
	self.handle_data('URLs referenced in this document:')
	self.end_p()
	self.start_small({})
	self.start_ol({'type':'[1]', 'compact':'compact'})
	for anchor, title in self._anchor_sequence:
	    self.do_li({})
	    if title:
		#  Set the title as a citation:
		self.start_cite({})
		self.handle_data(title)
		self.end_cite()
		self.handle_data(', ')
	    self.handle_data(anchor)
	self.end_ol()
	self.end_small()

    _inanchor = 0
    def start_a(self, attrs):
	href = None
	if attrs.has_key('href'):
	    baseurl = self.base or self._baseurl or ''
	    href = urlparse.urljoin(baseurl, attrs['href'])
	self.anchor = href
	if href:
	    if self._underline_anchors:
		self.formatter.push_style('underline')
		self._inanchor = 1
	    if not self._anchors.has_key(href):
		href = self.anchor = self._footnote_anchor(href, attrs)
		if self._anchors.has_key(href): return
		self._anchors[href] = len(self._anchor_sequence) + 1
		if attrs.has_key('title'):
		    title = string.strip(attrs['title'])
		    self._anchor_sequence.append((href, title))
		else:
		    self._anchor_sequence.append((href, None))
	else:
	    self._inanchor = 0

    def end_a(self):
	if self._underline_anchors and self._inanchor:
	    self.formatter.pop_style()
	if self.anchor:
	    anchor, self.anchor = self.anchor, None
	    old_size = self.formatter.writer.ps._font.font_size()
	    self.start_small({})
	    self.start_small({})
	    new_size = self.formatter.writer.ps._font.font_size()
	    yshift = old_size - (1.1 * new_size)
	    self.formatter.push_font((AS_IS, 0, 0, 0))
	    self.formatter.writer.ps.push_yshift(yshift)
	    self.handle_data('[%d]' % self._anchors[anchor])
	    self.formatter.writer.ps.pop_yshift()
	    self.formatter.pop_font()
	    self.end_small()
	    self.end_small()

    def end_title(self):
	HTMLParser.end_title(self)
	self.formatter.writer.ps.set_title(self.title)
	self.formatter.writer.ps.prune_titles()

    def start_small(self, attrs):
	font_size = 0.8 * self.formatter.writer.ps._font.font_size()
	self.formatter.push_font((font_size, None, None, None))

    def end_small(self):
	self.formatter.pop_font()

    def start_big(self, attrs):
	font_size = 1.2 * self.formatter.writer.ps._font.font_size()
	self.formatter.push_font((font_size, None, None, None))

    end_big = end_small

    def start_sup(self, attrs):
	font_size = self.formatter.writer.ps._font.font_size()
	self.start_small(attrs)
	new_font_size = self.formatter.writer.ps._font.font_size()
	yshift = font_size - (0.9 * new_font_size)
	self.formatter.writer.ps.push_yshift(yshift)

    def start_sub(self, attrs):
	self.start_small(attrs)
	new_font_size = self.formatter.writer.ps._font.font_size()
	self.formatter.writer.ps.push_yshift(-0.1 * new_font_size)

    def end_sup(self):
	self.formatter.writer.ps.pop_yshift()
	self.end_small()

    end_sub = end_sup

    def handle_image(self, src, alt, ismap, align, *notused):
	if self._image_loader:
	    imageurl = urlparse.urljoin(self._baseurl, src)
	    if self._image_cache.has_key(imageurl):
		image = self._image_cache[imageurl]
	    else:
		try:
		    image = self.load_image(imageurl)
		except EPSError:
		    self._image_cache[imageurl] = image = None
		else:
		    self._image_cache[imageurl] = image
	    if not image:
		#  previous load resulted in failure:
		self.handle_data(alt)
	    else:
		align = string.lower(align)
		self.formatter.writer.send_eps_data(image, align)
		self.formatter.assert_line_data()
	else:
	    self.handle_data(alt)

    def header_bgn(self, tag, level, attrs):
	HTMLParser.header_bgn(self, tag, level, attrs)
	dingbat = grailutil.extract_keyword('dingbat', attrs)
	if dingbat:
	    self.unknown_entityref(dingbat, '')
	    self.formatter.add_flowing_data(' ')
	elif attrs.has_key('src'):
	    self.do_img(attrs)
	    self.formatter.add_flowing_data(' ')

    # List attribute extensions:

    def start_ul(self, attrs, *args, **kw):
	self.list_check_dingbat(attrs)
	apply(HTMLParser.start_ul, (self, attrs) + args, kw)

    def do_li(self, attrs):
	self.list_check_dingbat(attrs)
	HTMLParser.do_li(self, attrs)

    def list_check_dingbat(self, attrs):
	if attrs.has_key('dingbat') and attrs['dingbat']:
	    img = self.load_dingbat(attrs['dingbat'])
	    if img: attrs['type'] = img

    # Override make_format():
    # This allows disc/circle/square to be mapped to images.

    def make_format(self, format, default='disc', listtype = None):
	fmt = format or default
	if fmt in ('disc', 'circle', 'square') and listtype == 'ul':
	    img = self.load_dingbat(fmt)
	    return img or HTMLParser.make_format(self, format, default)
	else:
	    return HTMLParser.make_format(self, format, default,
					  listtype = listtype)

    def unknown_entityref(self, entname, terminator):
	dingbat = self.load_dingbat(entname)
	if type(dingbat) is TupleType:
	    apply(self.formatter.writer.ps.push_font_string, dingbat)
	    self.formatter.assert_line_data()
	elif dingbat:
	    dingbat.set_size(self.formatter.writer.ps._font.font_size(),
			     self.formatter.writer.ps.get_pagewidth())
	    self.formatter.writer.send_eps_data(dingbat, 'absmiddle')
	    self.formatter.assert_line_data()
	else:
	    HTMLParser.unknown_entityref(self, entname, terminator)


    dingbats = {}			# (name, cog) ==> EPSImage
					#		  | (string, font)
					#		  | None

    fontdingbats = { 'disc': ('\x6c', 'ZapfDingbats'),
		     'circle': ('\x6d', 'ZapfDingbats'),
		     'square': ('\x6f', 'ZapfDingbats'),
		     'sp': (' ', None),
		     'thinsp': ('\240', None),
		     'endash': ('-', None)
		    }

    def load_dingbat(self, entname):
	"""Load the appropriate EPSImage object for an entity.
	"""
	if self._greyscale:
	    img = self.load_dingbat_cog(entname, 'grey')
	else:
	    img = self.load_dingbat_cog(entname, 'color')
	    if not img:
		img = self.load_dingbat_cog(entname, 'grey')
	return img

    def load_dingbat_cog(self, entname, cog):
	"""Load EPSImage object for an entity with a specified conversion.

	The conversion is not downgraded to grey if 'color' fails.  If the
	image is not available or convertible, returns None.
	"""
	key = (entname, cog)
	if self.dingbats.has_key(key):
	    return self.dingbats[key]
	gifname = entname + '.gif'
	epsname = os.path.join('eps.' + cog, entname + '.eps')
	self.dingbats[key] = None
	for p in self.iconpath:
	    epsp = os.path.join(p, epsname)
	    gifp = os.path.join(p, gifname)
	    if os.path.exists(epsp):
		self.load_dingbat_eps(key, epsp)
	    elif os.path.exists(gifp):
		try:
		    newepsp = convert_gif_to_eps(cog, gifp, epsp)
		except:
		    pass
		else:
		    self.load_dingbat_eps(key, newepsp)
		    if newepsp != epsp:
			os.unlink(newepsp)
		break
	return self.dingbats[key]

    def load_dingbat_eps(self, key, epsfile):
	"""Loads the EPSImage object and stores in the cache.
	"""
	try:
	    img = load_eps(epsfile)
	except EPSError:
	    #  no bounding box
	    self.dingbats[key] = None
	else:
	    self.dingbats[key] = img

    def load_image(self, imageurl):
	"""Load image and return EPS data and bounding box.

	If the conversion from raster data to EPS fails, the EPSError is
	raised.
	"""
	try:
	    image = self._image_loader(imageurl)
	except:
	    raise EPSError, 'Image could not be loaded.'
	if not image:
	    raise EPSError, 'Image could not be loaded.'
	import tempfile
	img_fn = tempfile.mktemp()
	fp = open(img_fn, 'wb')
	try:
	    fp.write(image)
	except:
	    raise EPSError, 'Failed to write image to external file.'
	fp.close()
	return load_image_file(img_fn, self._greyscale)


def load_image_file(img_fn, greyscale):
    """Generate EPS and the bounding box for an image stored in a file.

    This function attempts to use the Python Imaging Library if it is
    installed, otherwise it uses a fallback approach using external
    conversion programs.
    """
    import tempfile
    eps_fn = tempfile.mktemp()
    try:
	load_image_pil(img_fn, greyscale, eps_fn)
    except (AttributeError, IOError, ImportError):
	# AttributeError is possible with partial installation of PIL,
	# and IOError can mean a recognition failure.
	load_image_internal(img_fn, greyscale, eps_fn)
    img = load_eps(eps_fn)		# img is (data, bbox)
    os.unlink(eps_fn)
    return img


def load_image_internal(img_fn, greyscale, eps_fn):
    """Use external converters to generate EPS."""
    from imghdr import what
    imgtype = what(img_fn)
    if not imgtype:
	os.unlink(img_fn)
	raise EPSError, 'Could not identify image type.'
    cnv_key = (imgtype, (greyscale and 'grey') or 'color')
    if not image_converters.has_key(cnv_key):
	cnv_key = (imgtype, 'grey')
    if not image_converters.has_key(cnv_key):
	os.unlink(img_fn)
	raise EPSError, 'No converter defined for %s images.' % imgtype
    img_command = image_converters[cnv_key]
    img_command = img_command % {'i':img_fn, 'o':eps_fn}
    try:
	if os.system(img_command + ' 2>/dev/null'):
	    os.unlink(img_fn)
	    if os.path.exists(eps_fn):
		os.unlink(eps_fn)
	    raise EPSError, 'Error converting image to EPS.'
    except:
	if os.path.exists(img_fn):
	    os.unlink(img_fn)
	if os.path.exists(eps_fn):
	    os.unlink(eps_fn)
	raise EPSError, 'Could not run conversion process.'
    if os.path.exists(img_fn):
	os.unlink(img_fn)


def load_image_pil(img_fn, greyscale, eps_fn):
    """Use PIL to generate EPS."""
    import Image
    import traceback
    try:
	im = Image.open(img_fn)
	format = im.format
	if greyscale and im.mode not in ("1", "L"):
	    im = im.convert("L")
	im.save(eps_fn, "EPS")
    except:
	stdout = sys.stdout
	e, v, tb = sys.exc_type, sys.exc_value, sys.exc_traceback
	try:
	    sys.stdout = sys.stderr
	    traceback.print_exc()
	finally:
	    sys.stdout = stdout
	    raise e, v, tb


def load_eps(eps_fn):
    """Load an EPS image.

    The bounding box is extracted and stored together with the data in an
    EPSImage object.  If a PostScript `showpage' command is obvious in the
    file, it is removed.
    """
    fp = open(eps_fn)
    lines = fp.readlines()
    fp.close()
    try: lines.remove('showpage\n')
    except: pass			# o.k. if not found
    bbox = load_bounding_box(lines)
    return EPSImage(string.joinfields(lines, ''), bbox)


def load_bounding_box(lines):
    """Determine bounding box for EPS image given as sequence of text lines.
    """
    from string import lower
    bbox = None
    for line in lines:
	if len(line) > 21 and lower(line[:15]) == '%%boundingbox: ':
	    bbox = tuple(map(string.atoi, string.split(line[15:])))
	    break
    if not bbox:
	raise EPSError, 'Bounding box not specified.'
    return bbox


def convert_gif_to_eps(cog, giffile, epsfile):
    """Convert GIF to EPS using specified conversion.

    The EPS image is stored in `epsfile' if possible, otherwise a temporary
    file is created.  The name of the file created is returned.
    """
    if not image_converters.has_key(('gif', cog)):
	raise EPSError, "No conversion defined for %s GIFs." % cog
    try:
	fp = open(epsfile, 'w')
    except IOError:
	import tempfile
	filename = tempfile.mktemp()
    else:
	filename = epsfile
	fp.close()

    img_command = image_converters[('gif', cog)]
    img_command = img_command % {'i':giffile, 'o':filename}
    try:
	if os.system(img_command + ' 2>/dev/null'):
	    if os.path.exists(filename):
		os.unlink(filename)
	    raise EPSError, 'Error converting image to EPS.'
    except:
	if os.path.exists(filename):
	    os.unlink(filename)
	raise EPSError, 'Could not run conversion process.'

    return filename


def image_loader(url):
    """Simple image loader for the PrintingHTMLParser instance."""
    #
    # This needs a lot of work for efficiency and connectivity
    # with the rest of Grail, but works O.K. if there aren't many images
    # or if blocking can be tolerated.
    #
    from urllib import urlopen
    try:
	imgfp = urlopen(url)
    except IOError, msg:
	return None
    return imgfp.read()


# These functions and classes are "filters" which can be used as anchor
# transforms with the PrintingHTMLParser class.


def disallow_data_scheme(href, attrs):
    """Cancel data: URLs."""
    if urlparse.urlparse(href)[0] == 'data':
	href = None
    return href


def disallow_anchor_footnotes(href, attrs):
    """Cancel all anchor footnotes."""
    return None


class disallow_self_reference:
    """Cancel all anchor footnotes which refer to the current document."""
    def __init__(self, baseurl):
	parsed = urlparse.urlparse(baseurl)
	scheme, netloc, path, params, query, fragment = parsed
	self.__baseref = (scheme, netloc, path, params, query, '')

    def __call__(self, href, attrs):
	parsed = urlparse.urlparse(href)
	ref = parsed[:-1] + ('',)
	if ref == self.__baseref:
	    href = None
	return href


def main():
    global DEBUG, logfile
    import getopt
    import os
    help = None
    error = 0
    logfile = None
    paper = None
    title = ''
    url = ''
    #
    #  load preferences
    #
    prefs = {}
    load_prefs(os.path.join(script_dir, "grail-defaults"), prefs)
    load_prefs(os.path.join(grailutil.getgraildir(),
			    "grail-preferences"), prefs)
    #
    fontsize, leading = parse_fontsize(prefs['font-size'])
    footnote_anchors = string.atoi(prefs['footnote-anchors'])
    underline_anchors = string.atoi(prefs['underline-anchors'])
    orientation = prefs['orientation']
    greyscale = string.atoi(prefs['greyscale'])
    images = string.atoi(prefs['images'])
    #
    try:
	options, argv = getopt.getopt(sys.argv[1:], 'hdlaUu:t:s:p:o:')
    except getopt.error, err:
	error = 1
	help = 1
	options = ()
	sys.stderr.write("option failure: %s\n" % err)
    for opt, arg in options:
	if opt == '-h': help = 1
	elif opt == '-a': footnote_anchors = not footnote_anchors
	elif opt == '-d': DEBUG = 1
	elif opt == '-l': logfile = arg
	elif opt == '-o': orientation = arg
	elif opt == '-f': fontsize, leading = parse_fontsize(arg)
	elif opt == '-t': title = arg
	elif opt == '-u': url = arg
	elif opt == '-U': underline_anchors = not underline_anchors
	elif opt == '-c': greyscale = 0
	elif opt == '-p': paper = PaperInfo(arg)
    if help:
	stdout = sys.stderr
	progname = os.path.basename(sys.argv[0])
	try:
	    sys.stdout = sys.stderr
	    print 'Usage:', progname, '[options] [file-or-url]'
	    print '    -u: URL for footer'
	    print '    -t: title for header'
	    print '    -a: disable anchor footnotes'
	    print '    -U: disable anchor underlining'
	    print '    -o: orientation; portrait, landscape, or seascape'
	    print '    -p: paper size; letter, legal, a4, etc.'
	    print '    -f: font size, in points (default is %s/%s)' \
		  % (fontsize, leading)
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
	try:
	    infp = open(infile, 'r')
	except IOError:
	    # derive file object via URL; still needs to be HTML.
	    import urllib
	    infp = urllib.urlopen(infile)
	    import posixpath
	    outfile = posixpath.basename(urlparse.urlparse(infile)[2])
	    if not url:
		url = infile
	else:
	    outfile = infile
	outfile = os.path.splitext(outfile)[0] + '.ps'
	print 'Outputting PostScript to', outfile
	outfp = open(outfile, 'w')
    else:
	infile = None
	infp = sys.stdin
	outfp = sys.stdout
    if not paper:
	paper = PaperInfo(prefs['paper-size'])
    if orientation:
	try:
	    paper.rotate(orientation)
	except KeyError:
	    paper.rotate(string.atof(orientation))
    margins = map(string.atof, string.split(prefs['margins']))
    paper.set_margins(tuple(margins))
    # create the parsers
    w = PSWriter(outfp, title or None, url or '',
		 fontsize=fontsize, leading=leading, paper=paper)
    p = PrintingHTMLParser(w, baseurl=url, greyscale=greyscale,
			   underline_anchors=underline_anchors,
			   image_loader=(images and image_loader or None))
    if not footnote_anchors:
	p.add_anchor_transform(disallow_anchor_footnotes)
    elif url:
	p.add_anchor_transform(disallow_self_reference(url))
    p.feed(infp.read())
    p.close()
    w.close()


def parse_fontsize(spec):
    """Parse a font size with an optional leading specification.

    spec
	should be a string representing a real number or a pair of real
	numbers separated by a forward slash.  Whitespace is ignored.

    This function returns a tuple of the fontsize and leading.  If the
    leading is not specified by `spec', the leading will be the same as
    the font size.

    """
    if '/' in spec:
	spec = string.splitfields(spec, '/')
    else:
	spec = [spec, spec]
    if len(spec) != 2:
	raise ValueError, "illegal font size specification"
    spec = map(string.atof, map(string.strip, spec))
    return tuple(spec)


import regex
PREFS_re = regex.compile("printing--\([^:]*\):\(.*\)$", regex.casefold)

def load_prefs(filename, dict):
    try:
	fp = open(filename)
    except IOError:
	return dict
    while 1:
	line = fp.readline()
	if not line: break
	if PREFS_re.match(line) > -1:
	    key = string.lower(PREFS_re.group(1))
	    value = string.strip(PREFS_re.group(2))
	    dict[key] = value
    fp.close()
    return dict
    


# This PostScript causes the printer to use the named printer tray
# if possible, otherwise it simply proceeds in error.
# This must be formatter against the vars() of a PaperInfo instance.
setup_template = """%%%%BeginSetup
%%%%BeginPaperSize: %(PaperName)s
{
  statusdict begin /%(PaperName)stray where {
    pop %(PaperName)stray
  }{
    /%(PaperName)s where {
      pop %(PaperName)s
    }{
      (Don't know how to select %(PaperName)s paper.\\n) print
    } ifelse
  } ifelse
  end %% statusdict
} stopped pop
%%%%EndPaperSize
%%%%EndSetup
"""

# Load the PostScript prologue:
standard_header_file = grailutil.which(
    "header.ps", (script_dir, grailutil.getgraildir()))
if standard_header_file and os.path.exists(standard_header_file):
    standard_header_template = open(standard_header_file).read()
else:
    standard_header_template = None

# Allow the user to provide supplemental prologue material:
def get_userheader():
    fn = os.path.join(grailutil.getgraildir(), "custom.ps")
    if os.path.exists(fn):
	template = open(fn).read()
    else:
	template = ''
    return template, fn



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
