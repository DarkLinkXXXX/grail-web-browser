"""HTML parser class with support for applets and other Grail features."""

# XXX Need to split this in a perfectly safe module that knows about
# XXX anchors, images and subwindows, and a less safe module that
# XXX supports embedded applets.


from Tkinter import *
import os
import urlparse
import string
import tktools
import formatter
from ImageMap import MapThunk, MapInfo
from HTMLParser import HTMLParser, HeaderNumber
import AppletLoader
import grailutil
from grailutil import extract_attribute, extract_keyword

# Get rid of some methods so we can implement as extensions:
if hasattr(HTMLParser, 'do_isindex'):
    del HTMLParser.do_isindex
if hasattr(HTMLParser, 'do_link'):
    del HTMLParser.do_link

_inited = 0

def init_module(prefs):
    global _inited
    _inited = 1
    for opt in (1, 2, 3, 4, 5, 6):
	fmt = prefs.Get('parsing-html', 'format-h%d' % opt)
	HeaderNumber.set_default_format(opt - 1, eval(fmt))


class GrailHTMLParser(HTMLParser):

    object_aware_tags = ['param', 'alias', 'applet', 'script', 'object']

    def __init__(self, viewer, reload=0, autonumber=None):
	self.viewer = viewer
	self.reload = reload
	self.context = self.viewer.context
	self.app = self.context.app
	self.load_dingbat = self.app.load_dingbat
	self.style_stack = []
	self.loaded = []
	self.object_stack = []
	self.suppress_output = 0	# Length of object_stack at activation
	self.current_map = None
	self.target = None
	self.formatter_stack = [formatter.AbstractFormatter(self.viewer)]
	if autonumber is None:
	    if self.app.prefs.GetBoolean('parsing-html', 'autonumber-headers'):
		self.autonumber = 1
	if not _inited:
	    init_module(self.app.prefs)
	HTMLParser.__init__(self, self.formatter_stack[-1],
			    autonumber=autonumber)
	# Hackery so reload status can be reset when all applets are loaded
	self.reload1 = self.reload and AppletLoader.set_reload(self.context)
	if self.reload1:
	    self.reload1.attach(self)
	if self.app.prefs.GetBoolean('parsing-html', 'strict'):
	    self.restrict(0)

    def close(self):
	HTMLParser.close(self)
	if self.reload1:
	    self.reload1.detach(self)
	self.reload1 = None

    # Manage the object_stack

    def push_object(self, tag):
	self.object_stack.append(tag)
	return self.suppress_output

    def set_suppress(self):
	self.suppress_output = len(self.object_stack)
	self.handle_data = self.handle_data_noop

    def handle_data_noop(self, data):
	pass

    def pop_object(self):
	if self.suppress_output == len(self.object_stack):
	    self.suppress_output = 0
	    if self.nofill:
		self.handle_data = self.formatter.add_literal_data
	    else:
		self.handle_data = self.formatter.add_flowing_data
	    r = 1
	else:
	    r = 0
	del self.object_stack[-1]
	return r

    # manage the formatter stack
    def get_formatter(self):
	return self.formatter_stack[-1]

    def push_formatter(self, formatter):
	self.formatter_stack.append(formatter)
	self.formatter = formatter	## in base class
	if self.nofill:
	    self.handle_data = formatter.add_literal_data
	else:
	    self.handle_data = formatter.add_flowing_data
	self.viewer = self.formatter.writer
	self.context = self.viewer.context

    def pop_formatter(self):
	del self.formatter_stack[-1]
	self.formatter = self.formatter_stack[-1] ## in base class
	self.viewer = self.formatter.writer
	self.context = self.viewer.context
	if self.nofill:
	    self.handle_data = self.formatter.add_literal_data
	else:
	    self.handle_data = self.formatter.add_flowing_data

    # Override HTMLParser internal methods

    def handle_starttag(self, tag, method, attrs):
	if self.inhead and tag not in self.head_only_tags:
	    self.element_close_maybe('head', 'title', 'style')
	    self.inhead = 0
	    self.handle_starttag = self.handle_starttag_nohead
	elif not self.inhead:
	    if tag in self.head_only_tags:
		self.badhtml = 1
		self.handle_starttag = self.handle_starttag_nohead_isbad
	    else:
		self.handle_starttag = self.handle_starttag_nohead
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	method(attrs)

    def handle_starttag_nohead(self, tag, method, attrs):
	if tag in self.head_only_tags:
	    self.badhtml = 1
	    self.handle_starttag = self.handle_starttag_nohead_isbad
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	method(attrs)

    def handle_starttag_nohead_isbad(self, tag, method, attrs):
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	method(attrs)

    def handle_endtag(self, tag, method):
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	method()

    def handle_data_nohead(self, data):
	if not self.suppress_output:
	    HTMLParser.handle_data_nohead(self, data)

    def anchor_bgn(self, href, name, type, target=""):
	self.anchor = href
	self.target = target
	atag = utag = htag = otag = None
	if href:
	    atag = 'a'
	    utag = '>' + href
	    if target: utag = utag + '>' + target
	    self.viewer.bind_anchors(utag)
	    if self.app.global_history.inhistory_p(self.context.baseurl(href)):
		atag = 'ahist'
	if name:
	    ntag = '#' + name
	    self.viewer.add_target(ntag)
	    self.formatter.push_style(atag, utag, ntag)
	else:
	    self.formatter.push_style(atag, utag, None)

    def anchor_end(self):
	self.formatter.pop_style(3)
	self.anchor = self.target = None

    def do_hr(self, attrs):
	HTMLParser.do_hr(self, attrs)
	if attrs.has_key('noshade') and self.viewer.rules:
	    rule = self.viewer.rules[-1]
	    #  This seems to be a resaonable way to get contrasting colors.
	    rule.config(relief = FLAT,
			background = self.viewer.text['foreground'])

    # Duplicated from htmllib.py because we want to have the border attribute
    def do_img(self, attrs):
	align, usemap = CENTER, None
	extract = extract_keyword
	## align = extract('align', attrs, align, conv=conv_align)
	alt = extract('alt', attrs, '(image)')
	border = extract('border', attrs, 2, conv=string.atoi)
	ismap = attrs.has_key('ismap')
	src = extract('src', attrs, '')
	width = extract('width', attrs, 0, conv=string.atoi)
	height = extract('height', attrs, 0, conv=string.atoi)
	if attrs.has_key('usemap'):
	    # not sure how to assert(value[0] == '#')
	    value = attrs['usemap']
	    if value:
		if value[0] == '#': value = value[1:]
		usemap = MapThunk(self.context, value)
        self.handle_image(src, alt, usemap, ismap,
			  align, width, height, border, self.reload1)

    def handle_image(self, src, alt, usemap, ismap, align, width,
		     height, border=2, reload):
	from ImageWindow import ImageWindow
	window = ImageWindow(self.viewer, self.anchor, src, alt or "(Image)",
			     usemap, ismap, align, width, height,
			     border, self.target, reload)
	self.add_subwindow(window, align=align)

    def add_subwindow(self, w, align=CENTER):
	if self.formatter.nospace:
	    # XXX Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    self.viewer.prepare_for_insertion()
	self.viewer.add_subwindow(w, align=align)

    # Extend tag: </TITLE>

    def end_title(self):
	HTMLParser.end_title(self)
	self.context.set_title(self.title)
	if not self.inhead:
	    self.badhtml = 1

    # Override tag: <BODY colorspecs...>

    def start_body(self, attrs):
	HTMLParser.start_body(self, attrs)
	if not self.app.prefs.GetBoolean('parsing-html', 'honor-colors'):
	    return
	if attrs.has_key('bgcolor'):
	    clr = attrs['bgcolor']
	    if clr and clr[0] != '#':
		clr = '#' + clr
	    self.configcolor('background', clr)
	    #  Normally not important, but ISINDEX would cause
	    #  these to be non-empty:
	    for hr in self.viewer.rules + self.viewer.subwindows:
		hr.config(highlightbackground = clr)
	if attrs.has_key('text'):
	    self.configcolor('foreground', attrs['text'])
	if attrs.has_key('link'):
	    self.configcolor('foreground', attrs['link'], 'a')
	if attrs.has_key('vlink'):
	    self.configcolor('foreground', attrs['vlink'], 'ahist')
	if attrs.has_key('alink'):
	    self.configcolor('foreground', attrs['alink'], 'atemp')

    def configcolor(self, option, color, tag=None):
	if not color: return
	if color[0] != '#': color = '#' + color
	try:
	    if not tag:
		self.viewer.text[option] = color
	    else:
		apply(self.viewer.text.tag_config, (tag,), {option: color})
	except TclError, msg:
	    pass			# Ignore the error

    # Override tag: <BASE HREF=...>

    def do_base(self, attrs):
	base = None
	target = None
	if attrs.has_key('href'):
	    base = attrs['href']
	if attrs.has_key('target'):
	    target = attrs['target']
	self.context.set_baseurl(base, target)

    # New tag: <CENTER> (for Amy)

    def start_center(self, attrs):
	self.implied_end_p()
	self.formatter.push_alignment('center')

    def end_center(self):
	self.formatter.pop_alignment()

    # Duplicated from htmllib.py because we want to have the target attribute
    def start_a(self, attrs):
	href = name = type = target = ''
	has_key = attrs.has_key
	if has_key('href'): href = attrs['href']
	if has_key('name'): name = attrs['name']
	if has_key('type'): type = string.lower(attrs['type'])
	if has_key('target'): target = attrs['target']
        self.anchor_bgn(href, name, type, target)

    # New tag: <MAP> (for client side image maps)

    def start_map(self, attrs):
	# ignore maps without names
	if attrs.has_key('name'):
	    self.current_map = MapInfo(attrs['name'])
	else:
	    self.badhtml = 1

    def end_map(self):
	if self.current_map:
	    self.context.image_maps[self.current_map.name] = self.current_map
	    self.current_map = None

    # New tag: <AREA> (goes inside a map)

    def do_area(self, attrs):
	"""Handle the <AREA> tag."""

	if self.current_map:
	    extract = extract_keyword
	    shape = extract('shape', attrs, 'rect', conv=string.lower)
	    coords = extract('coords', attrs, '')
	    alt = extract('alt', attrs, '')
	    target = extract('target', attrs, '')
	    # not sure what the point of NOHREF is
	    url = extract('nohref', attrs, extract('href', attrs, ''))

	    try:
		self.current_map.add_shape(
		    shape, self.parse_area_coords(shape, coords), url, target)
	    except (IndexError, string.atoi_error):
		# wrong number of coordinates
		# how should this get reported to the user?
		self.badhtml = 1
		print "imagemap specifies bad coordinates"
		pass
	else:
	    self.badhtml = 1

    def parse_area_coords(self, shape, text):
	"""Parses coordinate string into list of numbers.

	Coordinates are stored differently depending on the shape of
	the object.

	Raise string.atoi_error when bad numbers occur.
	Raise IndexError when not enough coordinates are specified.
	
	"""
	import regsub
	
	coords = []
	
	terms = map(string.atoi, regsub.split(text, '[, ]+'))

	if shape == 'poly':
	    # list of (x,y) tuples
	    while len(terms) > 0:
		coords.append((terms[0], terms[1]))
		del terms[:2]
	    if coords[0] != coords[-1:]:
		# make sure the polygon is closed
		coords.append(coords[0])
	elif shape == 'rect':
	    # (x,y) tuples for upper left, lower right
	    coords.append((terms[0], terms[1]))
	    coords.append((terms[2], terms[3]))
	elif shape == 'circle':
	    # (x,y) tuple for center, followed by int for radius
	    coords.append((terms[0], terms[1]))
	    coords.append(terms[2])
	else:
	    self.badhtml = 1
	return coords

    # New tag: <APPLET>

    def start_applet(self, attrs):
	if self.push_object('applet'):
	    return
	# See http://www.javasoft.com/people/avh/applet.html for DTD
	extract = extract_keyword
	width = extract('width', attrs, conv=string.atoi)
	height = extract('height', attrs, conv=string.atoi)
	menu = extract('menu', attrs)
	code = extract('code', attrs)
	name = extract('name', attrs)
	codebase = extract('codebase', attrs)
	align = extract('align', attrs, 'baseline')
	vspace = extract('vspace', attrs)
	hspace = extract('hspace', attrs)
	apploader = AppletLoader.AppletLoader(
	    self, width=width, height=height,
	    menu=menu, name=name, code=code, codebase=codebase,
	    vspace=vspace, hspace=hspace, align=align, reload=self.reload1)
	if apploader.feasible():
	    self.apploader = apploader
	    self.set_suppress()
	else:
	    apploader.close()

    def end_applet(self):
	if self.pop_object():
	    self.apploader.go_for_it()

    # New tag: <PARAM>

    def do_param(self, attrs):
	if 0 < self.suppress_output == len(self.object_stack):
	    name = extract_keyword('name', attrs)
	    value = extract_keyword('value', attrs)
	    if name is not None and value is not None:
		self.apploader.set_param(name, value)

    # New tag: <APP> (for Grail 0.2 compatibility)

    def do_app(self, attrs):
	mod, cls, src = self.get_mod_class_src(attrs)
	if not (mod and cls): return
	width = extract_attribute('width', attrs, conv=string.atoi, delete=1)
	height = extract_attribute('height', attrs, conv=string.atoi, delete=1)
	menu = extract_attribute('menu', attrs, delete=1)
	mod = mod + ".py"
	apploader = AppletLoader.AppletLoader(
	    self, code=mod, name=cls, codebase=src,
	    width=width, height=height, menu=menu,
	    reload=self.reload1)
	if apploader.feasible():
	    for name, value in attrs.items():
		apploader.set_param(name, value)
	    apploader.go_for_it()
	else:
	    apploader.close()

    # Subroutines for <APP> tag parsing

    def get_mod_class_src(self, keywords):
	cls = extract_attribute('class', keywords, '', delete=1)
	src = extract_attribute('src', keywords, delete=1)
	if '.' in cls:
	    i = string.rfind(cls, '.')
	    mod = cls[:i]
	    cls = cls[i+1:]
	else:
	    mod = cls
	return mod, cls, src

    # New tag: <OBJECT> -- W3C proposal for <APPLET>/<IMG>/... merger.

    def start_object(self, attrs):
	if self.push_object('object'):
	    return
	extract = extract_keyword
	width = extract('width', attrs, conv=string.atoi)
	height = extract('height', attrs, conv=string.atoi)
	menu = extract('menu', attrs)
	classid = extract('classid', attrs)
	codebase = extract('codebase', attrs)
	align = extract('align', attrs, 'baseline')
	vspace = extract('vspace', attrs)
	hspace = extract('hspace', attrs)
	apploader = AppletLoader.AppletLoader(
	    self, width=width, height=height, menu=menu,
	    classid=classid, codebase=codebase,
	    vspace=vspace, hspace=hspace, align=align, reload=self.reload1)
	if apploader.feasible():
	    self.apploader = apploader
	    self.set_suppress()
	else:
	    apploader.close()

    def end_object(self):
	if self.pop_object():
	    self.apploader.go_for_it()

    # New tag: <SCRIPT> -- ignore anything inside it

    def start_script(self, attrs):
	if self.push_object('script'):
	    return
	self.set_suppress()

    def end_script(self):
	self.pop_object()

    # Heading support for dingbats (iconic entities):

    def header_bgn(self, tag, level, attrs):
	self.element_close_maybe('p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6')
	formatter = self.formatter
        formatter.end_paragraph(1)
	align = extract_keyword('align', attrs, conv=string.lower)
	formatter.push_alignment(align)
        formatter.push_font((tag, 0, 1, 0))
	self.header_number(tag, level, attrs)
	dingbat = extract_keyword('dingbat', attrs)
	if dingbat:
	    self.unknown_entityref(dingbat, '')
	    formatter.add_flowing_data(' ')
	    formatter.assert_line_data(0)
	elif attrs.has_key('src'):
	    self.do_img(attrs)
	    formatter.add_flowing_data(' ')
	    formatter.assert_line_data(0)

    def header_end(self, tag, level):
	formatter = self.formatter
	formatter.pop_alignment()
        formatter.pop_font()
        formatter.end_paragraph(1)

    # List attribute extensions:

    def start_ul(self, attrs):
	if attrs.has_key('dingbat'):
	    self.list_handle_dingbat(attrs)
	HTMLParser.start_ul(self, attrs)

    def do_li(self, attrs):
	if attrs.has_key('dingbat'):
	    self.list_handle_dingbat(attrs)
	HTMLParser.do_li(self, attrs)

    def list_handle_dingbat(self, attrs):
	if attrs['dingbat']:
	    img = self.load_dingbat(attrs['dingbat'])
	    if img: attrs['type'] = img

    # Override make_format():
    # This allows disc/circle/square to be mapped to dingbats.

    def make_format(self, format, default='disc'):
	fmt = format or default
	if fmt in ('disc', 'circle', 'square'):
	    img = self.load_dingbat(fmt)
	    return img or HTMLParser.make_format(self, format, default)
	else:
	    return HTMLParser.make_format(self, format, default)

    # Handle HTML extensions

    def unknown_starttag(self, tag, attrs):
	# Look up the function first, so it has a chance to update
	# the list of object aware tags
	if self.suppress_output:
	    if tag not in self.object_aware_tags:
		return
	function, as_dict, has_end = self.app.find_html_start_extension(tag)
	if function:
	    if not as_dict:
		attrs = attrs.items()
	    function(self, attrs)
	    if has_end:
		self.stack.append(tag)
	else:
	    self.badhtml = 1
	    if not self.inhead:
		self.handle_starttag = self.handle_starttag_nohead_isbad

    def unknown_endtag(self, tag):
	if self.suppress_output:
	    if tag not in self.object_aware_tags:
		return
	function = self.app.find_html_end_extension(tag)
	if function:
	    function(self)
	else:
	    self.badhtml = 1
	    if not self.inhead:
		self.handle_starttag = self.handle_starttag_nohead_isbad

    def report_unbalanced(self, tag):
	self.badhtml = 1
	if not self.inhead:
	    self.handle_starttag = self.handle_starttag_nohead_isbad

    # Handle proposed iconic entities (see W3C working drafts or HTML 3):

    def unknown_entityref(self, entname, terminator):
	if self.suppress_output:
	    return
	img = self.load_dingbat(entname)
	if img:
	    if type(img) is TupleType:
		s, tag = img
		if tag:
		    self.formatter.push_style(tag)
		    self.handle_data(s)
		    self.formatter.pop_style()
		else:
		    self.handle_data(s)
	    else:
		if self.formatter.nospace:
		    self.viewer.prepare_for_insertion()
		bgcolor = self.viewer.text['background']
		self.viewer.add_subwindow(Label(self.viewer.text, image = img,
						background = bgcolor,
						borderwidth = 0))
	    self.inhead = 0
	else:
	    #  Could not load image, allow parent class to handle:
	    HTMLParser.unknown_entityref(self, entname, terminator)



def conv_align(val):
    # This should work, but Tk doesn't actually do the right
    # thing so for now everything gets mapped to CENTER
    # alignment.
    return CENTER
    conv = grailutil.conv_enumeration(
	grailutil.conv_normstring(val),
	{'top': TOP,
	 'middle': CENTER,
	 'bottom': BASELINE,
	 # note: no HTML 2.0 equivalent of Tk's BOTTOM alignment
	 })
    if conv: return conv
    else: return CENTER
