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
from HTMLParser import HTMLParser
from Viewer import MIN_IMAGE_LEADER
import AppletLoader
import grailutil

# Get rid of some methods so we can implement as extensions:
if hasattr(HTMLParser, 'do_isindex'):
    del HTMLParser.do_isindex
if hasattr(HTMLParser, 'do_link'):
    del HTMLParser.do_link


class GrailHTMLParser(HTMLParser):

    insert_aware_tags = ['param', 'alias', 'applet']
    iconpath = ()

    def __init__(self, viewer, reload=0, iconpath=()):
	if iconpath:
	    self.iconpath = iconpath
	self.viewer = viewer
	self.reload = reload
	self.context = self.viewer.context
	self.app = self.context.app
	self.style_stack = []
	self.loaded = []
	self.insert_stack = []
	self.insert_active = 0		# Length of insert_stack at activation
	self.image_maps = {}            # for image maps
	self.current_map = None
	self.target = None
	self.formatter_stack = [formatter.AbstractFormatter(self.viewer)]
	self.headernumber = HeaderNumber()
	self.autonumber = self.app.prefs.GetBoolean('parsing-html',
						    'autonumber-headers')
	HTMLParser.__init__(self, self.formatter_stack[-1])
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

    # manage the formatter stack
    def get_formatter(self):
	return self.formatter_stack[-1]

    def push_formatter(self, formatter):
	self.formatter_stack.append(formatter)
	self.formatter = formatter	## in base class
	self.viewer = self.formatter.writer
	self.context = self.viewer.context

    def pop_formatter(self):
	del self.formatter_stack[-1]
	self.formatter = self.formatter_stack[-1] ## in base class
	self.viewer = self.formatter.writer
	self.context = self.viewer.context

    # Override HTMLParser internal methods

    def handle_starttag(self, tag, method, attrs):
	if self.inhead and tag not in self.head_only_tags:
	    self.element_close_maybe('head', 'title', 'style')
	    self.inhead = 0
	elif not self.inhead and tag in self.head_only_tags:
	    self.badhtml = 1
	if self.insert_active:
	    if tag not in self.insert_aware_tags:
		return
	method(attrs)

    def handle_endtag(self, tag, method):
	if self.insert_active:
	    if tag not in self.insert_aware_tags:
		return
	method()

    def handle_data(self, data):
	if not self.insert_active:
	    HTMLParser.handle_data(self, data)

    def anchor_bgn(self, href, name, type, target=""):
	self.element_close_maybe('a')	# cannot nest
	self.formatter_stack[-1].flush_softspace()
	self.anchor = href
	self.target = target
	atag = utag = htag = otag = None
	if href:
	    atag = 'a'
	    utag = '>' + href
	    if target: utag = utag + '>' + target
	    fulluri = self.context.baseurl(href)
	    if self.app.global_history.inhistory_p(fulluri):
		atag = 'ahist'
	ntag = name and '#' + name or None
	self.formatter_stack[-1].push_style(atag, utag, ntag)
	if utag:
	    self.viewer.bind_anchors(utag)

    def anchor_end(self):
	self.formatter_stack[-1].flush_softspace()
	self.formatter_stack[-1].pop_style(3)
	self.anchor = self.target = None

    def do_hr(self, attrs):
	HTMLParser.do_hr(self, attrs)
	if attrs.has_key('noshade'):
	    try:
		rule = self.viewer.rules[-1]
	    except:
		pass
	    else:
		rule['relief'] = FLAT
		rule['background'] = self.viewer.text['foreground']

    # Duplicated from htmllib.py because we want to have the border attribute
    def do_img(self, attrs):
	alt = '(image)'
	ismap = None
	usemap = None
	src = ''
	width = 0
	height = 0
	border = 2

	def conv_align(val):
	    # This should work, but Tk doesn't actually do the right
	    # thing so for now everything gets mapped to CENTER
	    # alignment.
	    return CENTER
## 	    conv = grailutil.conv_enumeration(
## 		grailutil.conv_normstring(val),
## 		{'top': TOP,
## 		 'middle': CENTER,
## 		 'bottom': BASELINE,
## 		 # note: no HTML 2.0 equivalent of Tk's BOTTOM alignment
## 		 })
## 	    if conv: return conv
## 	    else: return CENTER
	align = grailutil.extract_attribute('align', attrs,
					    conv=conv_align,
					    default=CENTER)

	extract = self.extract_keyword
	alt = extract('alt', attrs, '(image)')
	border = extract('border', attrs, 2, conv=string.atoi)
	if attrs.has_key('ismap'):
	    ismap = 1
	src = extract('src', attrs, '')
	width = extract('width', attrs, 0, conv=string.atoi)
	height = extract('height', attrs, 0, conv=string.atoi)
	if attrs.has_key('usemap'):
	    # not sure how to assert(value[0] == '#')
	    usemap = MapThunk (self, attrs['usemap'][1:])
        self.handle_image(src, alt, usemap, ismap,
			  align, width, height, border)

    def handle_image(self, src, alt, usemap, ismap, align, width,
		     height, border=2):
	from ImageWindow import ImageWindow
	window = ImageWindow(self.viewer, self.anchor, src, alt,
			     usemap, ismap, align, width, height,
			     border, self.target)
	self.add_subwindow(window, align=align)

    def add_subwindow(self, w, align=None):
	if self.formatter_stack[-1].nospace:
	    # XXX Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    self.handle_data(MIN_IMAGE_LEADER) # Non-breaking space
	if align is None:
	    self.viewer.add_subwindow(w)
	else:
	    self.viewer.add_subwindow(w, align=align)

    # Extend tag: </TITLE>

    def end_title(self):
	HTMLParser.end_title(self)
	self.context.set_title(self.title)

    # Override tag: <BODY colorspecs...>

    def start_body(self, attrs):
	self.element_close_maybe('head', 'style', 'title')
	self.inhead = 0
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
		hr.config(background = clr, highlightbackground = clr)
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
	self.formatter_stack[-1].push_style('center')

    def end_center(self):
	self.formatter_stack[-1].pop_style()

    # Duplicated from htmllib.py because we want to have the target attribute
    def start_a(self, attrs):
	extract = self.extract_keyword
        href = extract('href', attrs, '', conv=string.strip)
        name = extract('name', attrs, '', conv=string.strip)
	type = extract('type', attrs, '',
		       conv=lambda v,s=string: s.lower(s.strip(v)))
	target = extract('target', attrs, '', conv=string.strip)
        self.anchor_bgn(href, name, type, target)

    # New tag: <MAP> (for client side image maps)

    def start_map(self, attrs):
	# ignore maps without names
	if attrs.has_key('name'):
	    self.current_map = MapInfo(self, attrs['name'])

    def end_map(self):
	if self.current_map:
	    self.image_maps[self.current_map.name] = self.current_map
	    self.current_map = None

    # New tag: <AREA> (goes inside a map)

    def do_area(self, attrs):
	"""Handle the <AREA> tag."""

	if self.current_map:
	    extract = self.extract_keyword
	    shape = extract('shape', attrs, 'rect')
	    coords = extract('coords', attrs, '')
	    alt = extract('alt', attrs, '')
	    target = extract('target', attrs, '')
	    # not sure what the point of NOHREF is
	    url = extract('nohref', attrs, extract('href', attrs, ''))

	    try:
		self.current_map.add_shape(
		    shape, self.parse_area_coords(shape, coords), url, target)
	    except IndexError:
		# wrong number of coordinates
		# how should this get reported to the user?
		print "imagemap specifies bad coordinates"
		pass

    def parse_area_coords(self, shape, text):
	"""Parses coordinate string into list of numbers.

	Coordinates are stored differently depending on the shape of
	the object.
	"""
	coords = []
	terms = []

	string_terms = string.splitfields(text, ',')
	for i in range(len(string_terms)):
	    terms.append(string.atoi(string_terms[i]))

	if shape == 'poly':
	    # list of (x,y) tuples
	    while len(terms) > 0:
		coords.append((terms[0], terms[1]))
		del terms[0]
		del terms[0] # del terms[0:1] didn't work
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
	return coords

    # New tag: <APPLET>

    def start_applet(self, attrs):
	self.insert_stack.append('applet')
	if self.insert_active: return
	# See http://www.javasoft.com/people/avh/applet.html for DTD
	extract = self.extract_keyword
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
	    self.insert_active = len(self.insert_stack)
	else:
	    apploader.close()

    def end_applet(self):
	if self.insert_active == len(self.insert_stack):
	    self.insert_active = 0
	    self.apploader.go_for_it()
	del self.insert_stack[-1]

    # New tag: <PARAM>

    def do_param(self, attrs):
	if 0 < self.insert_active == len(self.insert_stack):
	    name = self.extract_keyword('name', attrs)
	    value = self.extract_keyword('value', attrs)
	    if name is not None and value is not None:
		self.apploader.set_param(name, value)

    # New tag: <APP>

    def do_app(self, attrs):
	mod, cls, src = self.get_mod_class_src(attrs)
	if not (mod and cls): return
	width = self.extract_keyword('width', attrs, conv=string.atoi)
	height = self.extract_keyword('height', attrs, conv=string.atoi)
	menu = self.extract_keyword('menu', attrs)
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
	cls = self.extract_keyword('class', keywords)
	src = self.extract_keyword('src', keywords)
	if cls and '.' in cls:
	    i = string.rfind(cls, '.')
	    mod = cls[:i]
	    cls = cls[i+1:]
	else:
	    mod = cls
	return mod, cls, src

    def extract_keyword(self, key, keywords, default=None, conv=None):
	if keywords.has_key(key):
	    value = keywords[key]
	    del keywords[key]
	    if not conv:
		return value
	    try:
		return conv(value)
	    except:
		return default
	else:
	    return default

    # Heading support for dingbats (iconic entities):

    def start_h1(self, attrs):
	self.header_bgn('h1', 0, attrs)

    def start_h2(self, attrs):
	self.header_bgn('h2', 1, attrs)

    def start_h3(self, attrs):
	self.header_bgn('h3', 2, attrs)

    def start_h4(self, attrs):
	self.header_bgn('h4', 3, attrs)

    def start_h5(self, attrs):
	self.header_bgn('h5', 4, attrs)

    def start_h6(self, attrs):
	self.header_bgn('h6', 5, attrs)

    def header_bgn(self, tag, level, attrs):
	self.close_paragraph()
        self.formatter.end_paragraph(1)
	align = self.extract_keyword('align', attrs, conv=string.lower)
	self.formatter.push_style(align)
        self.formatter.push_font((tag, 0, 1, 0))
	if self.autonumber:
	    self.headernumber.incr(level, attrs)
	    self.formatter.add_flowing_data(self.headernumber.string(level))
	dingbat = self.extract_keyword('dingbat', attrs)
	if dingbat:
	    self.unknown_entityref(dingbat, '')
	    self.formatter.send_flowing_data(' ')
	    self.formatter.assert_line_data(0)
	elif attrs.has_key('src'):
	    self.do_img(attrs)
	    self.formatter.send_flowing_data(' ')
	    self.formatter.assert_line_data(0)

    def header_end(self):
	self.formatter.pop_style()
        self.formatter.pop_font()
        self.formatter.end_paragraph(1)

    end_h1 = end_h2 = end_h3 = end_h4 = end_h5 = end_h6 = header_end

    # List attribute extensions:

    def start_ul(self, attrs):
	self.list_check_dingbat(attrs)
	HTMLParser.start_ul(self, attrs)

    def do_li(self, attrs):
	self.list_check_dingbat(attrs)
	HTMLParser.do_li(self, attrs)

    def list_check_dingbat(self, attrs):
	if attrs.has_key('dingbat') and attrs['dingbat']:
	    img = self.load_dingbat(attrs['dingbat'])
	    if img: attrs['type'] = img

    # Override make_format():
    # This allows disc/circle/square to be mapped to images.

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
	# the list of insert-aware tags
	if self.insert_active:
	    if tag not in self.insert_aware_tags:
		return
	function, as_dict = self.app.find_html_start_extension(tag)
	if function:
	    if not as_dict:
		attrs = attrs.items()
	    function(self, attrs)

    def unknown_endtag(self, tag):
	if self.insert_active:
	    if tag not in self.insert_aware_tags:
		return
	function = self.app.find_html_end_extension(tag)
	if function:
	    function(self)

    # Handle proposed iconic entities (see W3C working drafts or HTML 3):

    entityimages = {}

    def load_dingbat(self, entname):
	try:
	    return self.entityimages[entname]
	except KeyError:
	    pass
	gifname = grailutil.which(entname + '.gif', self.iconpath)
	if gifname:
	    img = PhotoImage(file=gifname)
	    self.entityimages[entname] = img
	    return img
	self.entityimages[entname] = None
	return None

    def unknown_entityref(self, entname, terminator):
	img = self.load_dingbat(entname)
	if img:
	    bgcolor = self.viewer.text['background']
	    self.add_subwindow(Label(self.viewer.text, image = img,
				     background = bgcolor,
				     borderwidth = 0))
	else:
	    HTMLParser.unknown_entityref(self, entname, terminator)



class HeaderNumber:
    def __init__(self):
	self.numbers = [0, 0, 0, 0, 0, 0]
	self.formats = ['',
			'%(h2)d ',
			'%(h2)d.%(h3)d ',
			'%(h2)d.%(h3)d.%(h4)d ',
			'%(h2)d.%(h3)d.%(h4)d.%(h5)d ',
			'%(h2)d.%(h3)d.%(h4)d.%(h5)d.%(h6)d ']

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

