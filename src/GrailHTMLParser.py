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
from AppletLoader import AppletLoader

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
	HTMLParser.__init__(self, self.formatter_stack[-1])
	if self.app.prefs.GetBoolean('parsing-html', 'strict'):
	    self.restrict(0)

    def close(self):
	HTMLParser.close(self)

    # manage the formatter stack
    def get_formatter(self):
	return self.formatter_stack[-1]

    def push_formatter(self, formatter):
	self.formatter_stack.append(formatter)
	self.formatter = formatter	## in base class

    def pop_formatter(self):
	del self.formatter_stack[-1]
	self.formatter = self.formatter_stack[-1] ## in base class

    # Override HTMLParser internal methods

    def handle_starttag(self, tag, method, attrs):
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

    # Duplicated from htmllib.py because we want to have the border attribute
    def do_img(self, attrs):
	align = ''
	alt = '(image)'
	ismap = None
	usemap = None
	src = ''
	width = 0
	height = 0
	border = 2

	extract = self.extract_keyword
	align = extract('align', attrs, conv=string.lower)
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
	self.add_subwindow(window)

    def add_subwindow(self, w):
	if self.formatter_stack[-1].nospace:
	    # XXX Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    self.handle_data("\240") # Non-breaking space
	self.viewer.add_subwindow(w)

    # Extend tag: </TITLE>

    def end_title(self):
	HTMLParser.end_title(self)
	self.context.set_title(self.title)

    # Override tag: <BODY colorspecs...>

    def start_body(self, attrs):
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

    def configcolor(self, option, color):
	if not color: return
	if color[0] != '#': color = '#' + color
	try:
	    self.viewer.text[option] = color
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
	apploader = AppletLoader(self,
				 width=width, height=height, menu=menu,
				 name=name, code=code, codebase=codebase,
				 vspace=vspace, hspace=hspace, align=align,
				 reload=self.reload)
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
	apploader = AppletLoader(self, code=mod, name=cls, codebase=src,
				 width=width, height=height, menu=menu,
				 reload=self.reload)
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

    def start_style(self, attrs):
	"""Disable display of document data -- this is a style sheet.
	"""
	self.savedata = ''

    def end_style(self):
	"""Re-enable data display.
	"""
	self.savedata = None

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

    # Handle proposed iconic entities (see W3C working drafts):

    entityimages = {}

    def unknown_entityref(self, entname):
	try:
	    img = self.entityimages[entname]
	except KeyError:
	    gifname = entname + '.gif'
	    for p in self.iconpath:
		p = os.path.join(p, gifname)
		if os.path.exists(p):
		    img = PhotoImage(file=p)
		    self.entityimages[entname] = img
		    w = Label(self.viewer.text, image = img)
		    self.add_subwindow(w)
		    return
	    self.entityimages[entname] = None
	    self.handle_data('&%s;' % entname)
	else:
	    if img:
		self.add_subwindow(Label(self.viewer.text, image = img))
