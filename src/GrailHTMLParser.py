# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

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
import Viewer
from HTMLParser import HTMLParser, HeaderNumber
import grailutil
from grailutil import extract_attribute, extract_keyword

URL_VALUED_ATTRIBUTES = ['href', 'src', 'codebase']

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

    def __init__(self, viewer, reload=0):
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
	self.formatter_stack = []
	self.push_formatter(formatter.AbstractFormatter(self.viewer))
	if not _inited:
	    init_module(self.app.prefs)
	HTMLParser.__init__(self, self.get_formatter())
	self._ids = {}
	# Hackery so reload status can be reset when all applets are loaded
	import AppletLoader
	self.reload1 = self.reload and AppletLoader.set_reload(self.context)
	if self.reload1:
	    self.reload1.attach(self)
	if self.app.prefs.GetBoolean('parsing-html', 'strict'):
	    self.restrict(0)
	# Information from <META ... CONTENT="..."> is collected here.
	# Entries are KEY --> [(NAME, HTTP-EQUIV, CONTENT), ...], where
	# KEY is (NAME or HTTP-EQUIV).
	self._metadata = {}

    def close(self):
	HTMLParser.close(self)
	if self.reload1:
	    self.reload1.detach(self)
	self.reload1 = None
	refresh = None
	if self._metadata.has_key("refresh"):
	    name, http_equiv, refresh = self._metadata["refresh"][0]
	elif self.context.get_headers().has_key("refresh"):
	    refresh = self.context.get_headers()["refresh"]
	if refresh:
	    DynamicReloader(self.context, refresh)

    # Manage the object_stack

    def push_object(self, tag):
	self.object_stack.append(tag)
	return self.suppress_output

    def set_suppress(self):
	self.suppress_output = len(self.object_stack)
	self.set_data_handler(self.handle_data_noop)

    def handle_data_noop(self, data):
	pass

    def pop_object(self):
	if self.suppress_output == len(self.object_stack):
	    self.suppress_output = 0
	    if self.nofill:
		handler = self.formatter.add_literal_data
	    else:
		handler = self.formatter.add_flowing_data
	    self.set_data_handler(handler)
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
	self.set_formatter(formatter)

    def pop_formatter(self):
	del self.formatter_stack[-1]
	self.set_formatter(self.formatter_stack[-1])

    def set_formatter(self, formatter):
	self.formatter = formatter	## in base class
	self.viewer = formatter.writer
	self.context = self.viewer.context
	if self.nofill:
	    self.set_data_handler(formatter.add_literal_data)
	else:
	    self.set_data_handler(formatter.add_flowing_data)

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
	massage_attributes(attrs)
	method(attrs)
	if attrs.has_key('id'):
	    self.register_id(attrs['id'])

    def handle_starttag_nohead(self, tag, method, attrs):
	if tag in self.head_only_tags:
	    self.badhtml = 1
	    self.handle_starttag = self.handle_starttag_nohead_isbad
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	#massage_attributes(attrs)   *** inlined for performance: ***
	for k in URL_VALUED_ATTRIBUTES:
	    if attrs.has_key(k) and attrs[k]:
		attrs[k] = string.joinfields(string.split(attrs[k]), '')
	method(attrs)
	if attrs.has_key('id'):
	    self.register_id(attrs['id'])

    def handle_starttag_nohead_isbad(self, tag, method, attrs):
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	#massage_attributes(attrs)   *** inlined for performance: ***
	for k in URL_VALUED_ATTRIBUTES:
	    if attrs.has_key(k) and attrs[k]:
		attrs[k] = string.joinfields(string.split(attrs[k]), '')
	method(attrs)
	if attrs.has_key('id'):
	    self.register_id(attrs['id'])

    def handle_endtag(self, tag, method):
	if self.suppress_output and tag not in self.object_aware_tags:
	    return
	method()

    def handle_data_nohead(self, data):
	if not self.suppress_output:
	    HTMLParser.handle_data_nohead(self, data)

    def register_id(self, id):
	if self._ids.has_key(id):
	    self.badhtml = 1
	    return 0
	self._ids[id] = id
	self.viewer.add_target('#' + id)
	return 1

    def anchor_bgn(self, href, name, type, target="", id=None):
	self.anchor = href
	self.target = target
	atag, utag, idtag = None, None, None
	if href:
	    atag = 'a'
	    if target:
		utag = '>%s%s%s' % (href, Viewer.TARGET_SEPARATOR, target)
	    else:
		utag = '>' + href
	    self.viewer.bind_anchors(utag)
	    if self.app.global_history.inhistory_p(self.context.baseurl(href)):
		atag = 'ahist'
	if id and self.register_id(id):
	    idtag = id and ('#' + id) or None
	if name and self.register_id(name):
	    self.formatter.push_style(atag, utag, '#' + name, idtag)
	else:
	    self.formatter.push_style(atag, utag, None, idtag)

    def anchor_end(self):
	self.formatter.pop_style(4)
	self.anchor = self.target = None

    def do_hr(self, attrs):
	if attrs.has_key('src') and self.app.load_images:
	    align = extract_keyword('align', attrs, default='center',
		    conv=lambda s,gu=grailutil: gu.conv_enumeration(
			gu.conv_normstring(s), ['left', 'center', 'right']))
	    self.implied_end_p()
	    self.formatter.push_alignment(align)
	    self.do_img({'border': '0',
			 'src': attrs['src']})
	    self.formatter.pop_alignment()
	    self.formatter.add_line_break()
	else:
	    HTMLParser.do_hr(self, attrs)
	    if attrs.has_key('noshade') and self.viewer.rules:
		rule = self.viewer.rules[-1]
		#  This seems to be a resaonable way to get contrasting colors.
		rule.config(relief = FLAT,
			    background = self.viewer.text['foreground'])

    # Duplicated from htmllib.py because we want to have the border attribute
    def do_img(self, attrs):
	align, usemap = BASELINE, None
	extract = extract_keyword
	## align = extract('align', attrs, align, conv=conv_align)
	alt = extract('alt', attrs, '(image)')
	border = extract('border', attrs, self.anchor and 2 or None,
			 conv=string.atoi)
	ismap = attrs.has_key('ismap')
	if ismap and border is None: border = 2
	src = extract('src', attrs, '')
	width = extract('width', attrs, 0, conv=string.atoi)
	height = extract('height', attrs, 0, conv=string.atoi)
	hspace = extract('hspace', attrs, 0, conv=string.atoi)
	vspace = extract('vspace', attrs, 0, conv=string.atoi)
	if attrs.has_key('usemap'):
	    # not sure how to assert(value[0] == '#')
	    value = string.strip(attrs['usemap'])
	    if value:
		if value[0] == '#': value = string.strip(value[1:])
		from ImageMap import MapThunk
		usemap = MapThunk(self.context, value)
		if border is None: border = 2
        self.handle_image(src, alt, usemap, ismap,
			  align, width, height, border or 0, self.reload1,
			  hspace=hspace, vspace=vspace)

    def handle_image(self, src, alt, usemap, ismap, align, width,
		     height, border=2, reload, hspace=0, vspace=0):
	if not self.app.prefs.GetBoolean("browser", "load-images"):
	    self.handle_data(alt)
	    return
	from ImageWindow import ImageWindow
	window = ImageWindow(self.viewer, self.anchor, src, alt or "(Image)",
			     usemap, ismap, align, width, height,
			     border, self.target, reload)
	self.add_subwindow(window, align=align, hspace=hspace, vspace=vspace)

    def add_subwindow(self, w, align=CENTER, hspace=0, vspace=0):
	self.formatter.flush_softspace()
	if self.formatter.nospace:
	    # XXX Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    self.viewer.prepare_for_insertion()
	self.viewer.add_subwindow(w, align=align)
	if hspace or vspace:
	    self.viewer.text.window_config(w, padx=hspace, pady=vspace)
	self.formatter.assert_line_data()

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
	from grailutil import conv_normstring
	bgcolor = extract_keyword('bgcolor', attrs, conv=conv_normstring)
	if bgcolor:
	    clr = self.configcolor('background', bgcolor)
	    if clr:
		#  Normally not important, but ISINDEX would cause
		#  these to be non-empty, as would all sorts of illegal stuff:
		for hr in self.viewer.rules + self.viewer.subwindows:
		    hr.config(highlightbackground = clr)
	self.configcolor('foreground',
			 extract_keyword('text', attrs, conv=conv_normstring))
	self.configcolor('foreground',
			 extract_keyword('link', attrs, conv=conv_normstring),
			 'a')
	self.configcolor('foreground',
			 extract_keyword('vlink', attrs, conv=conv_normstring),
			 'ahist')
	self.configcolor('foreground',
			 extract_keyword('alink', attrs, conv=conv_normstring),
			 'atemp')

    # These are defined by the HTML 3.2 (Wilbur) version of HTML.
    _std_colors = {"black": "#000000",
		   "silver": "#c0c0c0",
		   "gray": "#808080",
		   "white": "#ffffff",
		   "maroon": "#800000",
		   "red": "#ff0000",
		   "purple": "#800080",
		   "fuchsia": "#ff00ff",
		   "green": "#008000",
		   "lime": "#00ff00",
		   "olive": "#808000",
		   "yellow": "#ffff00",
		   "navy": "#000080",
		   "blue": "#0000ff",
		   "teal": "#008080",
		   "aqua": "#00ffff",
		   }

    def configcolor(self, option, color, tag=None):
	"""Set a color option, returning the color that was actually used.

	If no color was set, `None' is returned.
	"""
	if not color:
	    return None
	c = self.try_configcolor(option, color, tag)
	if color[0] != '#' and not c:
	    c = self.try_configcolor(option, '#' + color, tag)
	if not c and self._std_colors.has_key(color):
	    color = self._std_colors[color]
	    c = self.try_configcolor(option, color, tag)
	return c

    def try_configcolor(self, option, color, tag):
	try:
	    if tag:
		apply(self.viewer.text.tag_config, (tag,), {option: color})
	    else:
		self.viewer.text[option] = color
	except TclError, msg:
	    return None
	else:
	    return color

    # Override tag: <BASE HREF=...>

    def do_base(self, attrs):
	base = None
	target = None
	if attrs.has_key('href'):
	    base = attrs['href']
	if attrs.has_key('target'):
	    target = attrs['target']
	self.context.set_baseurl(base, target)

    # Override tag: <META ...>

    def do_meta(self, attrs):
	# CONTENT='...' is required;
	# at least one of HTTP-EQUIV=xyz or NAME=xyz is required.
	if not attrs.has_key("content") \
	   or not (attrs.has_key("http-equiv") or attrs.has_key("name")):
	    self.badhtml = 1
	    return
	name = extract_keyword("name", attrs, conv=grailutil.conv_normstring)
	http_equiv = extract_keyword("http-equiv", attrs,
				     conv=grailutil.conv_normstring)
	key = name or http_equiv
	content = extract_keyword("content", attrs, conv=string.strip)
	item = (name, http_equiv, content)
	if self._metadata.has_key(key):
	    self._metadata[key].append(item)
	else:
	    entries = self._metadata[key] = [item]

    # Duplicated from htmllib.py because we want to have the target attribute
    def start_a(self, attrs):
	href = name = type = target = ''
	id = None
	has_key = attrs.has_key
	if has_key('href'): href = attrs['href']
	if has_key('name'): name = attrs['name']
	if has_key('type'): type = string.lower(attrs['type'] or '')
	if has_key('target'): target = attrs['target']
	if has_key('id'): id = attrs['id']
        self.anchor_bgn(href, name, type, target, id)

    # New tag: <MAP> (for client side image maps)

    def start_map(self, attrs):
	# ignore maps without names
	if attrs.has_key('name'):
	    from ImageMap import MapInfo
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
	    if shape == 'polygon':
		shape = 'poly'
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
	vspace = extract('vspace', attrs, 0, conv=string.atoi)
	hspace = extract('hspace', attrs, 0, conv=string.atoi)
	import AppletLoader
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
	import AppletLoader
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
	vspace = extract('vspace', attrs, 0, conv=string.atoi)
	hspace = extract('hspace', attrs, 0, conv=string.atoi)
	import AppletLoader
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
	HTMLParser.header_bgn(self, tag, level, attrs)
	dingbat = extract_keyword('dingbat', attrs)
	if dingbat:
	    self.unknown_entityref(dingbat, '')
	    self.formatter.add_flowing_data(' ')
	elif attrs.has_key('src'):
	    self.do_img(attrs)
	    self.formatter.add_flowing_data(' ')

    # List attribute extensions:

    def start_ul(self, attrs, tag='ul'):
	if attrs.has_key('dingbat'):
	    self.list_handle_dingbat(attrs)
	elif attrs.has_key('src'):
	    self.list_handle_src(attrs)
	HTMLParser.start_ul(self, attrs, tag=tag)

    def do_li(self, attrs):
	if attrs.has_key('dingbat'):
	    if self.list_stack:
		if self.list_stack[-1][0] == 'ul':
		    self.list_handle_dingbat(attrs)
	    else:
		self.list_handle_dingbat(attrs)
	elif attrs.has_key('src'):
	    if self.list_stack:
		if self.list_stack[-1][0] == 'ul':
		    self.list_handle_src(attrs)
	    else:
		self.list_handle_src(attrs)
	HTMLParser.do_li(self, attrs)

    def list_handle_dingbat(self, attrs):
	if attrs['dingbat']:
	    img = self.load_dingbat(attrs['dingbat'])
	    if img: attrs['type'] = img

    def list_handle_src(self, attrs):
	if not self.app.prefs.GetBoolean("browser", "load-images"):
	    return
	src = string.joinfields(string.split(attrs['src']), '')
	image = self.context.get_async_image(src, self.reload)
	if image: attrs['type'] = image

    # Override make_format():
    # This allows disc/circle/square to be mapped to dingbats.

    def make_format(self, format, default='disc', listtype=None):
	fmt = format or default
	if type(fmt) is StringType:
	    fmt = string.lower(fmt)
	if fmt in ('disc', 'circle', 'square'):
	    if listtype == 'ul':
		img = self.load_dingbat(fmt)
		return img or HTMLParser.make_format(self, format, default,
						     listtype = listtype)
	    else:
		return '1.'
	else:
	    return HTMLParser.make_format(self, format, default,
					  listtype = listtype)

    # Handle HTML extensions

    def unknown_starttag(self, tag, attrs):
	# Look up the function first, so it has a chance to update
	# the list of object aware tags
	if self.suppress_output:
	    if tag not in self.object_aware_tags:
		return
	function, as_dict, has_end = self.app.find_html_start_extension(tag)
	if function:
	    id = attrs.has_key('id') and attrs['id'] or None
	    if not as_dict:
		attrs = attrs.items()
	    function(self, attrs)
	    if id:
		self.register_id(id)
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
		    tag = (self.formatter.writer.fonttag or '') + tag
		    self.formatter.push_style(tag)
		    self.handle_data(s)
		    self.formatter.pop_style()
		else:
		    self.handle_data(s)
	    else:
		bgcolor = self.viewer.text['background']
		label = Label(self.viewer.text, image=img,
			      background=bgcolor, borderwidth=0)
		self.add_subwindow(label)
		# these bindings need to be done *after* the add_subwindow()
		# call to get the right <Button-3> binding.
		if self.anchor:
		    thunk = IconicEntityLinker(self.viewer,
					       self.anchor, self.target)
		    label.bind("<ButtonPress-1>", thunk.button_1_press)
		    label.bind("<ButtonRelease-1>", thunk.button_1_release)
		    label.bind("<ButtonPress-2>", thunk.button_2_press)
		    label.bind("<ButtonRelease-2>", thunk.button_2_release)
		    label.bind("<Button-3>", thunk.button_3_event)
		    label.bind("<Enter>", thunk.enter)
		    label.bind("<Leave>", thunk.leave)
	    self.inhead = 0
	else:
	    #  Could not load image, allow parent class to handle:
	    HTMLParser.unknown_entityref(self, entname, terminator)


class IconicEntityLinker:
    __here = None

    def __init__(self, viewer, url, target):
	self.__target = target or ''
	self.__url = url
	self.__viewer = viewer

    def activate_link(self, event):
	self.__here = self.__viewer.text.index(At(event.x, event.y))
	tag = ">" + self.__url
	if self.__target:
	    tag = tag + Viewer.TARGET_SEPARATOR + self.__target
	raw = self.__viewer.text.tag_ranges(tag)
	list = []
	for i in range(0, len(raw), 2):
	    list.append((raw[i], raw[i+1]))
	if list:
	    self.__viewer._atemp = list
	    for (start, end) in list:
		self.__viewer.text.tag_add('atemp', start, end)

    def button_1_press(self, event):
	self.__viewer.text.focus_set()
	self.activate_link(event)

    def button_1_release(self, event):
	here = self.__viewer.text.index(At(event.x, event.y))
	if here == self.__here:
	    self.__viewer.context.follow(self.__url, target=self.__target)

    def button_2_press(self, event):
	self.activate_link(event)

    def button_2_release(self, event):
	here = self.__viewer.text.index(At(event.x, event.y))
	if here != self.__here:
	    return
	viewer = self.__viewer
	url = viewer.context.get_baseurl(self.__url)
	viewer.master.update_idletasks()
	import Browser
	app = viewer.context.app
	b = Browser.Browser(app.root, app)
	b.context.load(url)
	viewer.remove_temp_tag(histify=1)

    def button_3_event(self, event=None):
	url = self.__viewer.context.get_baseurl(self.__url)
	self.__viewer.open_popup_menu(event, link_url=url)

    def enter(self, event=None):
	target = self.__target
	if not self.__target:
	    target = self.__viewer.context.get_target()
	if target:
	    message = "%s in %s" % (self.__url, target)
	else:
	    message = self.__url
	self.__viewer.enter_message(message)

    def leave(self, event=None):
	self.__here = None
	self.__viewer.leave_message()
	self.__viewer.remove_temp_tag()


class DynamicReloader:
    def __init__(self, context, spec):
	self.__context = context
	self.__starting_url = context.get_baseurl()
	seconds, url = self.parse(spec)
	if seconds is None:		# parse failed
	    return
	self.__target_url = url
	ms = int(seconds * 1000)	# convert to milliseconds
	if ms:
	    context.viewer.master.after(ms, self.load)
	else:
	    self.load()

    def load(self):
	context = self.__context
	if context.get_baseurl() == self.__starting_url \
	   and context.viewer.text:
	    same_page = (self.__starting_url == self.__target_url)
	    if same_page:
		context.load_from_history(context.history.peek(0), reload=1)
	    else:
		context.load(self.__target_url)

    def parse(self, spec):
	if ";" in spec:
	    pos = string.find(spec, ";")
	    spec = "%s %s" % (spec[:pos], spec[pos + 1:])
	specitems = string.split(spec)
	if not specitems:
	    return None, None
	try:
	    seconds = string.atof(specitems[0])
	except ValueError:
	    return None, None
	if seconds < 0:
	    return None, None
	if len(specitems) > 1:
	    specurl = specitems[1]
	    if len(specurl) >= 4 and string.lower(specurl[:4]) == "url=":
		specurl = specurl[4:]
	    url = self.__context.get_baseurl(specurl)
	else:
	    url = self.__context.get_baseurl()
	return seconds, url


def conv_align(val):
    # This should work, but Tk doesn't actually do the right
    # thing so for now everything gets mapped to BASELINE
    # alignment.
    return BASELINE
    conv = grailutil.conv_enumeration(
	grailutil.conv_normstring(val),
	{'top': TOP,
	 'middle': CENTER,		# not quite right
	 'bottom': BASELINE,
	 'absbottom': BOTTOM,		# compatibility hack...
	 'absmiddle': CENTER,		# compatibility hack...
	 })
    if conv: return conv
    else: return CENTER


def massage_attributes(attrs):
    # Removes superfluous whitespace in common URL-valued attributes:
    for k in URL_VALUED_ATTRIBUTES:
	if attrs.has_key(k) and attrs[k]:
	    attrs[k] = string.joinfields(string.split(attrs[k]), '')

