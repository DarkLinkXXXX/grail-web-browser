"""HTML 2.0 parser.

See the HTML 2.0 specification:
http://www.w3.org/hypertext/WWW/MarkUp/html-spec/html-spec_toc.html
"""

import sys

if __name__ == '__main__':
    sys.path.insert(0, '../pythonlib')

import regsub
import string
from types import StringType
import SGMLLexer
from SGMLParser import SGMLParser
from formatter import AS_IS


class HTMLParser(SGMLParser):

    from htmlentitydefs import entitydefs

    doctype = 'html'
    head_only_tags = ('link', 'meta', 'title', 'isindex', 'range',
		      'base', 'nextid', 'style', 'head', 'html')
    autonumber = None
    savedata = None
    title = base = anchor = nextid = None
    nofill = badhtml = 0
    inhead = 1

    def __init__(self, formatter, verbose=0):
        SGMLParser.__init__(self, verbose)
	self.restrict(1)
        self.formatter = formatter
        self.anchor = None
        self.anchorlist = []
        self.list_stack = []
	self.headernumber = HeaderNumber()

    def close(self):
	SGMLParser.close(self)
	#  Clean out circular reference:
	if self.__dict__.has_key('handle_data'):
	    del self.__dict__['handle_data']

    # ------ Methods used internally; some may be overridden

    # --- Formatter interface, taking care of 'savedata' mode;
    # shouldn't need to be overridden

    def handle_data_head(self, data):
	if string.strip(data) != '':
	    self.element_close_maybe('head', 'script', 'style', 'title')
	    self.inhead = 0
	    self.set_data_handler(self.formatter.add_flowing_data)
	    self.handle_data(data)

    handle_data = handle_data_head	# always start in head

    def handle_data_save(self, data):
	self.savedata[0] = self.savedata[0] + data

    # --- Hooks to save data; shouldn't need to be overridden

    def save_bgn(self):
	if self.savedata:
	    self.savedata.insert(0, '')
	else:
	    self.savedata = ['']
	self.set_data_handler(self.handle_data_save)

    def save_end(self):
	if self.savedata:
	    data = self.savedata[0]
	    del self.savedata[0]
	    if not self.savedata:	# deal with cheaters
		self.savedata = None
	else:
	    data = ''
	if not self.savedata:
	    if self.inhead:
		handler = self.handle_data_head
	    elif self.nofill:
		handler = self.formatter.add_literal_data
	    else:
		handler = self.formatter.add_flowing_data
	    self.set_data_handler(handler)
	if not self.nofill:
	    data = string.join(string.split(data))
	return data

    def push_nofill(self):
        self.nofill = self.nofill + 1
	self.set_data_handler(self.formatter.add_literal_data)

    def pop_nofill(self):
        self.nofill = max(0, self.nofill - 1)
	if not self.nofill:
	    self.set_data_handler(self.formatter.add_flowing_data)

    # --- Hooks for anchors; should probably be overridden

    def anchor_bgn(self, href, name, type):
        self.anchor = href
        if href:
	    self.anchorlist.append(href)

    def anchor_end(self):
        if self.anchor:
	    self.handle_data("[%d]" % len(self.anchorlist))
	    self.anchor = None

    # --- Hook for images; should probably be overridden

    def handle_image(self, src, alt, *args):
        self.handle_data(alt)

    # --------- Top level elememts

    def start_html(self, attrs): pass
    def end_html(self): pass

    def start_head(self, attrs): pass
    def end_head(self):
	self.inhead = 0

    def start_body(self, attrs):
	self.element_close_maybe('head', 'style', 'script', 'title')
	self.inhead = 0

    def end_body(self): pass

    # ------ Head elements

    def start_title(self, attrs):
        self.save_bgn()

    def end_title(self):
        self.title = self.save_end()

    def do_base(self, attrs):
	if attrs.has_key('href'):
	    self.base = attrs['href']

    def do_isindex(self, attrs):
        self.isindex = 1

    def do_link(self, attrs):
        pass

    def do_meta(self, attrs):
        pass

    def do_nextid(self, attrs):		# Deprecated, but maintain the state.
	self.element_close_maybe('style', 'title')
	if attrs.has_key('n'):
	    self.nextid = attrs['n']
	    self.badhtml = self.badhtml or not self.inhead
	else:
	    self.badhtml = 1

    def start_style(self, attrs):
	"""Disable display of document data -- this is a style sheet.
	"""
	self.save_bgn()

    def end_style(self):
	"""Re-enable data display.
	"""
	self.save_end()

    # ------ Body elements

    # --- Headings

    def start_h1(self, attrs):
	self.header_bgn('h1', 0, attrs)

    def end_h1(self):
	self.header_end('h1', 0)

    def start_h2(self, attrs):
	self.header_bgn('h2', 1, attrs)

    def end_h2(self):
	self.header_end('h2', 1)

    def start_h3(self, attrs):
	self.header_bgn('h3', 2, attrs)

    def end_h3(self):
	self.header_end('h3', 2)

    def start_h4(self, attrs):
	self.header_bgn('h4', 3, attrs)

    def end_h4(self):
	self.header_end('h4', 3)

    def start_h5(self, attrs):
	self.header_bgn('h5', 4, attrs)

    def end_h5(self):
	self.header_end('h5', 4)

    def start_h6(self, attrs):
	self.header_bgn('h6', 5, attrs)

    def end_h6(self):
	self.header_end('h6', 5)

    def header_bgn(self, tag, level, attrs):
	self.element_close_maybe('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
	if self.strict_p():
	    self.close_paragraph()
	    while self.list_stack:
		self.badhtml = 1
		self.lex_endtag(self.list_stack[0][0])
        self.formatter.end_paragraph(1)
	if attrs.has_key('align'):
	    align = attrs['align']
	    if align: align = string.lower(align)
	else:
	    align = None
	self.formatter.push_alignment(align)
        self.formatter.push_font((tag, 0, 1, 0))
	self.header_number(tag, level, attrs)

    def header_end(self, tag, level):
        self.formatter.pop_font()
	self.formatter.pop_alignment()
        self.formatter.end_paragraph(1)

    def header_number(self, tag, level, attrs):
	if self.autonumber is None:
	    if attrs.has_key('seqnum') or attrs.has_key('skip'):
		self.autonumber = 1
	self.headernumber.incr(level, attrs)
	if self.autonumber:
	    self.formatter.add_flowing_data(self.headernumber.string(level))

    # --- Block Structuring Elements

    def start_p(self, attrs):
	self.close_paragraph()
        self.formatter.end_paragraph(1)
	align = None
	if attrs.has_key('align') and attrs['align']:
	    align = string.lower(attrs['align'])
	self.formatter.push_alignment(align)

    def end_p(self, parbreak = 1):
	self.formatter.pop_alignment()
        self.formatter.end_paragraph(parbreak)

    def implied_end_p(self):
	if 'p' in self.stack:
	    #  Remove all but the <P>
	    while self.stack[-1] != 'p':
		self.lex_endtag(self.stack[-1])
	    #  Remove <P> surgically:
	    del self.stack[-1]
	    self.end_p(parbreak = 0)
	self.formatter.add_line_break()

    start_div = start_p
    end_div = end_p

    def start_pre(self, attrs):
	self.close_paragraph()
        self.formatter.end_paragraph(1)
        self.formatter.push_font((AS_IS, AS_IS, AS_IS, 1))
	self.formatter.push_alignment('left')
	self.push_nofill()

    def end_pre(self):
	self.pop_nofill()
	self.formatter.pop_alignment()
        self.formatter.end_paragraph(1)
        self.formatter.pop_font()

    def start_xmp(self, attrs):
        self.start_pre(attrs)
        #self.setliteral('xmp') # Tell SGML parser

    def end_xmp(self):
        self.end_pre()

    def start_listing(self, attrs):
        self.start_pre(attrs)
        #self.setliteral('listing') # Tell SGML parser

    def end_listing(self):
        self.end_pre()

    def start_address(self, attrs):
	self.do_br({})
        self.formatter.push_font((AS_IS, 1, AS_IS, AS_IS))

    def end_address(self):
	self.do_br({})
        self.formatter.pop_font()

    def start_blockquote(self, attrs):
	self.close_paragraph()
        self.formatter.end_paragraph(1)
        self.formatter.push_margin('blockquote')
        self.formatter.push_style('blockquote')

    def end_blockquote(self):
	self.close_paragraph()		# may be paragraphs in blockquotes
        self.formatter.end_paragraph(1)
        self.formatter.pop_margin()
        self.formatter.pop_style()

    # --- List Elements

    #	The document's list structure is stored in a stack called
    #	self.list_stack.  Each element of the stack is a list with
    #	the entries:
    #
    #	    [element, label, entry_count, compact_p, stack_depth]
    #
    #	Where element can be 'dd', 'dl', 'ol', 'ul' (no 'dt');
    #	      label is the item label (for 'ol', 'ul' only) for
    #		subsequent list items.  If this is a string, it is
    #		handled as a format string, otherwise it must be
    #		interpretable by the add_label_data() method of the
    #		writer;
    #	      entry_count is the expected index of the next list
    #	        item - 1;
    #	      compact_p is a boolean (*must* be 0 or 1) set to true
    #		if COMPACT is set for the list (not implied by being
    #		in Grail) for the current list or an enclosing list;
    #	      stack_depth is the depth of the element stack when the
    #		list was opened.  This is used to close all elements
    #		opened within a previous list item without having to
    #		check for specific elements.

    def start_lh(self, attrs):
	margin = None
	if self.list_stack:
	    self.list_trim_stack()
	    listtype = self.list_stack[-1][0]
	    if listtype == 'dl':
		margin = 'lh'
	elif 'p' in self.stack:
	    self.badhtml = 1
	    self.lex_endtag('p')
	self.do_br({})
	self.formatter.push_font(('', 1, 1, 0))
	self.formatter.push_margin(margin)
	if not self.list_stack:
	    self.badhtml = 1

    def end_lh(self):
	self.formatter.pop_margin()
	self.formatter.pop_font()
	if self.list_stack:
	    self.formatter.end_paragraph(not self.list_stack[-1][3])
	else:
	    self.formatter.end_paragraph(1)

    def start_ul(self, attrs):
	self.element_close_maybe('p', 'lh')
	if self.list_stack:
	    self.formatter.end_paragraph(0)
	    compact = self.list_stack[-1][3]
	else:
	    self.formatter.end_paragraph(1)
	    compact = 0
        self.formatter.push_margin('ul')
	if attrs.has_key('plain'):
	    label = ''
	else:
	    if attrs.has_key('type'):
		format = attrs['type']
	    else:
		format = ('disc', 'circle', 'square')[len(self.list_stack) % 3]
	    label = self.make_format(format, listtype='ul')
        self.list_stack.append(['ul', label, 0,
				#  Propogate COMPACT once set:
				compact or attrs.has_key('compact'),
				len(self.stack) + 1])

    def end_ul(self):
        if self.list_stack:
	    del self.list_stack[-1]
	if self.list_stack:
	    self.implied_end_p()
	    if self.formatter.have_label:
		self.formatter.assert_line_data()
	    self.formatter.add_line_break()
	else:
	    self.close_paragraph()
	    if self.formatter.have_label:
		self.formatter.assert_line_data()
	    self.formatter.end_paragraph(1)
        self.formatter.pop_margin()

    def do_li(self, attrs):
        if not self.list_stack:
	    self.fake_li(attrs)
	    return
	if 'p' in self.stack:		# ugly hack to compact trailing <P>
	    self.implied_end_p()	# even though list_trim_stack() will
	self.list_trim_stack()		# close it.
	[listtype, label, counter, compact, depth] = top = self.list_stack[-1]
	if attrs.has_key('type'):
	    s = attrs['type']
	    if type(s) is StringType:
		label = top[1] = self.make_format(s, label, listtype=listtype)
	    elif s:
		label = s
	if listtype == 'ol':
	    if attrs.has_key('seqnum'):
		try: top[2] = counter = \
			      string.atoi(string.strip(attrs['seqnum']))
		except: top[2] = counter = counter+1
	    elif attrs.has_key('value'):
		try: top[2] = counter = \
			      string.atoi(string.strip(attrs['value']))
		except: top[2] = counter = counter+1
	    else:
		top[2] = counter = counter+1
	    if attrs.has_key('skip'):
		try: top[2] = counter = counter + string.atoi(attrs['skip'])
		except: pass
	self.formatter.add_label_data(label, counter)

    def fake_li(self, attrs):
	#  Illegal, but let's try not to be ugly:
	self.badhtml = 1
	self.element_close_maybe('p', 'lh')
	self.formatter.end_paragraph(0)
	format = '*'
	if attrs.has_key('type') and (type(attrs['type']) is StringType):
	    format = self.make_format(attrs['type'], format)
	else:
	    format = self.make_format(format, 'disc', listtype='ul')
	if type(format) is StringType:
	    data = self.formatter.format_counter(format, 1) + ' '
	    self.formatter.add_flowing_data(data)

    def make_format(self, format, default='*', listtype=None):
	if not format:
	    format = default
	if format in ('1', 'a', 'A', 'i', 'I') and listtype == 'ol':
	    format = format + '.'
	elif type(format) is not StringType:
	    pass
	elif listtype == 'ul':
	    format = '*'
	else:
	    format = string.strip(format)
	return format

    def start_ol(self, attrs):
	self.close_paragraph()
	if self.list_stack:
	    self.formatter.end_paragraph(0)
	    compact = self.list_stack[-1][3]
	else:
	    self.formatter.end_paragraph(1)
	    compact = 0
        self.formatter.push_margin('ol')
	if attrs.has_key('type'):
	    label = self.make_format(attrs['type'], '1', listtype='ol')
	else:
	    label = '1.'
	start = 0
	if attrs.has_key('seqnum'):
	    try: start = string.atoi(attrs['seqnum']) - 1
	    except: pass
	elif attrs.has_key('start'):
	    try: start = string.atoi(attrs['start']) - 1
	    except: pass
        self.list_stack.append(['ol', label, start,
				compact or attrs.has_key('compact'),
				len(self.stack) + 1])

    def end_ol(self):
	self.end_ul()

    def start_menu(self, attrs):
	attrs['plain'] = None
        self.start_ul(attrs)

    def end_menu(self):
        self.end_ul()

    def start_dir(self, attrs):
	attrs['plain'] = None
	attrs['wrap'] = 'horiz'
        self.start_ul(attrs)

    def end_dir(self):
        self.end_ul()

    def start_dl(self, attrs):
	margin = None
	if self.list_stack:
	    self.implied_end_p()
	    self.formatter.end_paragraph(0)
	    if self.list_stack[-1][3]:
		attrs['compact'] = None
	    if self.list_stack[-1][0] == 'dl':
		margin = 'dl'
	    attrs['compact'] = None
	else:
	    self.close_paragraph()
	    self.formatter.end_paragraph(1)
	self.formatter.push_margin(margin)
        self.list_stack.append(['dl', '', 0, attrs.has_key('compact'),
				len(self.stack) + 1])

    def end_dl(self):
        self.ddpop(not (self.list_stack and self.list_stack[-1][3]))
        if self.list_stack: del self.list_stack[-1]
	self.formatter.pop_margin()

    def do_dt(self, attrs):
        self.ddpop()

    def do_dd(self, attrs):
        self.ddpop()
        self.formatter.push_margin('dd')
	self.formatter.have_label = 1
	compact = self.list_stack and self.list_stack[-1][3]
        self.list_stack.append(['dd', '', 0, compact, len(self.stack) + 1])

    def ddpop(self, bl=0):
	self.element_close_maybe('lh', 'p')
        self.formatter.end_paragraph(bl)
	if not self.list_stack or self.list_stack[-1][0] not in ('dl', 'dd'):
	    # we're not already in a DL, so imply one.
	    # this isn't perfect compatibility, but keeps grail from
	    # dying a horrible death.
	    self.lex_starttag('dl', {})
	    self.badhtml = 1
        if self.list_stack and self.list_stack[-1][0] == 'dd':
	    del self.list_stack[-1]
	    self.list_trim_stack()
	    self.formatter.pop_margin()

    def list_trim_stack(self):
	if not self.list_stack:
	    return
	depth = self.list_stack[-1][4]
	while len(self.stack) > depth:
	    self.lex_endtag(self.stack[depth])

    # --- Phrase Markup

    # Idiomatic Elements

    def start_cite(self, attrs): self.start_i(attrs)
    def end_cite(self): self.end_i()

    def start_code(self, attrs): self.start_tt(attrs)
    def end_code(self): self.end_tt()

    def start_del(self, attrs):
	self.formatter.push_font((AS_IS, 1, AS_IS, AS_IS))
	self.formatter.push_style('red')
    def end_del(self):
	self.formatter.pop_style()
	self.formatter.pop_font()

    def start_ins(self, attrs):
	self.formatter.push_font((AS_IS, 1, AS_IS, AS_IS))
	self.formatter.push_style('ins')
    def end_ins(self):
	self.formatter.pop_style()
	self.formatter.pop_font()

    def start_dfn(self, attrs): self.start_i(attrs)
    def end_dfn(self): self.end_i()

    def start_em(self, attrs): self.start_i(attrs)
    def end_em(self): self.end_i()

    def start_kbd(self, attrs): self.start_tt(attrs)
    def end_kbd(self): self.end_tt()

    def start_samp(self, attrs): self.start_tt(attrs)
    def end_samp(self): self.end_tt()

    def start_strike(self, attrs):
	self.formatter.push_style('overstrike', 'red')
    def end_strike(self):
	self.formatter.pop_style(2)

    def start_strong(self, attrs): self.start_b(attrs)
    def end_strong(self): self.end_b()

    def start_var(self, attrs): self.start_i(attrs)
    def end_var(self): self.end_i()

    # Typographic Elements

    def start_i(self, attrs):
	self.formatter.push_font((AS_IS, 1, AS_IS, AS_IS))
    def end_i(self):
	self.formatter.pop_font()

    def start_b(self, attrs):
	self.formatter.push_font((AS_IS, AS_IS, 1, AS_IS))
    def end_b(self):
	self.formatter.pop_font()

    def start_tt(self, attrs):
	self.formatter.push_font((AS_IS, AS_IS, AS_IS, 1))
    def end_tt(self):
	self.formatter.pop_font()

    def start_u(self, attrs):
	self.formatter.push_style('underline')
    def end_u(self):
	self.formatter.pop_style()

    def start_s(self, attrs):
	self.formatter.push_style('overstrike')
    def end_s(self):
	self.formatter.pop_style()

    def start_a(self, attrs):
        href = ''
        name = ''
        type = ''
	if attrs.has_key('href'):
	    href = string.strip(attrs['href'])
	if attrs.has_key('name'):
	    name = string.strip(attrs['name'])
	if attrs.has_key('type'):
	    type = string.lower(string.strip(attrs['type']))
        self.anchor_bgn(href, name, type)

    def end_a(self):
        self.anchor_end()

    # --- Line Break

    def do_br(self, attrs):
        self.formatter.add_line_break()

    # --- Horizontal Rule

    def do_hr(self, attrs):
	self.implied_end_p()
	if attrs.has_key('width'):
	    abswidth, percentwidth = self.parse_width(attrs['width'])
	else:
	    abswidth, percentwidth = None, 1.0
	height = align = None
	if attrs.has_key('size'):
	    try: height = string.atoi(attrs['size'])
	    except: pass
	    else: height = max(1, height)
	if attrs.has_key('align'):
	    try: align = string.lower(attrs['align'])
	    except: pass
        self.formatter.add_hor_rule(abswidth, percentwidth, height, align)

    def parse_width(self, str):
	str = string.strip(str or '')
	if not str:
	    return None, None
	wid = percent = None
	if str[-1] == '%':
	    try: percent = string.atoi(str[:-1])
	    except: pass
	    else: percent = min(1.0, max(0.0, (0.01 * percent)))
	else:
	    try: wid = max(0, string.atoi(str))
	    except: pass
	    else: wid = wid or None
	return wid, percent

    # --- Image

    def do_img(self, attrs):
        align = ''
        alt = '(image)'
        ismap = ''
        src = ''
	width = 0
	height = 0
	if attrs.has_key('align'):
	    align = string.lower(attrs['align'])
	if attrs.has_key('alt'):
	    alt = attrs['alt']
	if attrs.has_key('ismap'):
	    ismap = 1
	if attrs.has_key('src'):
	    src = string.strip(attrs['src'])
	if attrs.has_key('width'):
	    try: width = string.atoi(attrs['width'])
	    except: pass
	if attrs.has_key('height'):
	    try: height = string.atoi(attrs['height'])
	    except: pass
        self.handle_image(src, alt, ismap, align, width, height)

    # --- Really Old Unofficial Deprecated Stuff

    def do_plaintext(self, attrs):
        self.start_pre(attrs)
        self.setnomoretags() # Tell SGML parser

    # --- Unhandled lexical tokens:

    def unknown_starttag(self, tag, attrs):
        self.badhtml = 1

    def unknown_endtag(self, tag):
        self.badhtml = 1

    def unknown_entityref(self, entname, terminator):
	self.badhtml = 1
	self.handle_data('%s%s%s' % (SGMLLexer.ERO, entname, terminator))

    def report_unbalanced(self, tag):
	self.badhtml = 1

    # --- Utilities:

    def element_close_maybe(self, *elements):
	"""Handle any open elements on the stack of the given types.

	`elements' should be a tuple of all element types which must be
	closed if they exist on the stack.  Sequence is not important.
	"""
	for elem in elements:
	    if elem in self.stack:
		self.lex_endtag(elem)

    def close_paragraph(self):
	if 'p' in self.stack:
	    self.lex_endtag('p')



class HeaderNumber:
    formats = ['',
	       '%(h2)d. ',
	       '%(h2)d.%(h3)d. ',
	       '%(h2)d.%(h3)d.%(h4)d. ',
	       '%(h2)d.%(h3)d.%(h4)d.%(h5)d. ',
	       '%(h2)d.%(h3)d.%(h4)d.%(h5)d.%(h6)d. ']

    def __init__(self, formats=None):
	self.numbers = [0, 0, 0, 0, 0, 0]
	if formats and len(formats) >= 6:
	    self.formats = map(None, formats)
	else:
	    self.formats = map(None, self.formats)

    def incr(self, level, attrs):
	numbers = self.numbers
	i = level
	while i < 5:
	    i = i + 1
	    numbers[i] = 0
	if attrs.has_key('skip'):
	    try: skip = string.atoi(attrs['skip'])
	    except: skip = 0
	else:
	    skip = 0
	if attrs.has_key('seqnum'):
	    try: numbers[level] = string.atoi(attrs['seqnum'])
	    except: pass
	    else: return
	numbers[level] = numbers[level] + 1 + skip

    def string(self, level, format = None):
	if format is None:
	    format = self.formats[level]
	numbers = self.numbers
	numdict = {'h1': numbers[0],
		   'h2': numbers[1],
		   'h3': numbers[2],
		   'h4': numbers[3],
		   'h5': numbers[4],
		   'h6': numbers[5]}
	return format % numdict

    def get_format(self, level):
	return self.formats[level]

    def get_all_formats(self):
	return tuple(self.formats)

    def set_format(self, level, s):
	self.formats[level] = s

    def set_default_format(self, level, s):
	HeaderNumber.formats[level] = s

HeaderNumber.set_default_format = HeaderNumber().set_default_format



def test():
    import sys
    file = 'test.html'
    if sys.argv[1:]: file = sys.argv[1]
    fp = open(file, 'r')
    data = fp.read()
    fp.close()
    from formatter import NullWriter, AbstractFormatter
    w = NullWriter()
    f = AbstractFormatter(w)
    p = HTMLParser(f)
    p.feed(data)
    p.close()


if __name__ == '__main__':
    test()
