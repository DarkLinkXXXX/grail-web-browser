"""HTML parser class with support for applets and other Grail features."""

# XXX Need to split this in a perfectly safe module that knows about
# XXX anchors, images and subwindows, and a less safe module that
# XXX supports embedded applets.


from Tkinter import *
import htmllib
import urlparse
import string
import tktools
import formatter
from AppletLoader import AppletLoader


# Get rid of do_isindex method so we can implement it as an extension
if hasattr(htmllib.HTMLParser, 'do_isindex'):
    del htmllib.HTMLParser.do_isindex


class AppletHTMLParser(htmllib.HTMLParser):

    insert_aware_tags = ['param', 'alias', 'insert', 'applet', 'embed']

    def __init__(self, viewer, reload=0):
	self.viewer = viewer
	self.reload = reload
	self.context = self.viewer.context
	self.app = self.context.app
	self.style_stack = []
	self.loaded = []
	self.page_tag_count = 0
	self.insert_stack = []
	self.insert_active = 0		# Length of insert_stack at activation
	self.formatter = formatter.AbstractFormatter(self.viewer)
	htmllib.HTMLParser.__init__(self, self.formatter)

    def close(self):
	htmllib.HTMLParser.close(self)

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
	    htmllib.HTMLParser.handle_data(self, data)

    def anchor_bgn(self, href, name, type):
	self.formatter.flush_softspace()
	self.anchor = href
	atag = utag = htag = otag = None
	if href:
	    atag = 'a'
	    utag = '>' + href
	    otag = '%%%d' % self.page_tag_count
	    self.page_tag_count = self.page_tag_count + 1
	    fulluri = self.context.baseurl(href)
	    if self.app.global_history.inhistory_p(fulluri):
		htag = 'ahist'
	ntag = name and '#' + name or None
	self.formatter.push_style(atag)
	self.formatter.push_style(utag)
	self.formatter.push_style(ntag)
	self.formatter.push_style(otag)
	self.formatter.push_style(htag)
	if utag:
	    self.viewer.bind_anchors(utag)

    def anchor_end(self):
	self.formatter.flush_softspace()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.anchor = None

    # Duplicated from htmllib.py because we want to have the border attribute
    def do_img(self, attrs):
	align = ''
	alt = '(image)'
	ismap = ''
	usemap = ''
	src = ''
	width = 0
	height = 0
	border = 2
        for attrname, value in attrs:
            if attrname == 'align':
                align = value
            if attrname == 'alt':
                alt = value
            if attrname == 'border':
		try: border = string.atoi(value)
		except: pass
            if attrname == 'ismap':
                ismap = value
            if attrname == 'src':
                src = value
	    if attrname == 'width':
		try: width = string.atoi(value)
		except: pass
	    if attrname == 'height':
		try: height = string.atoi(value)
		except: pass
	    if attrname == 'usemap':
		usemap = value
        self.handle_image(src, alt, usemap or ismap,
			  align, width, height, border)

    def handle_image(self, src, alt, ismap, align, width, height, border=2):
	from ImageWindow import ImageWindow
	window = ImageWindow(self.viewer, self.anchor,
			     src, alt, ismap, align,
			     width, height, border)
	self.add_subwindow(window)

    def add_subwindow(self, w):
	if self.formatter.nospace:
	    # XXX Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    self.handle_data("\240") # Non-breaking space
	self.viewer.add_subwindow(w)

    # Extend tag: </TITLE>

    def end_title(self):
	htmllib.HTMLParser.end_title(self)
	self.context.set_title(self.title)

    # Override tag: <BODY colorspecs...>

    def start_body(self, attrs):
	dict = {'bgcolor': None, 'text': None,
		'link': None, 'vlink': None, 'alink': None}
	for name, value in attrs:
	    dict[name] = value
	self.configcolor('background', dict['bgcolor'])
	self.configcolor('foreground', dict['text'])

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
        for a, v in attrs:
            if a == 'href':
                base = v
	self.context.set_baseurl(base)

    # New tag: <CENTER> (for Amy)

    def start_center(self, attrs):
	self.formatter.push_style('center')

    def end_center(self):
	self.formatter.pop_style()

    # New tag: <INSERT> (for the time being, same as <APPLET>)

    def start_insert(self, attrs):
	self.start_applet(attrs)

    def end_insert(self):
	self.end_applet()

    # New tag: <APPLET>

    def start_applet(self, attrs):
	self.insert_stack.append('applet')
	if self.insert_active: return
	keywords = self.get_keywords(attrs)
	# See http://www.javasoft.com/people/avh/applet.html for DTD
	width = self.extract_keyword('width', keywords, conv=string.atoi)
	height = self.extract_keyword('height', keywords, conv=string.atoi)
	menu = self.extract_keyword('menu', keywords)
	code = self.extract_keyword('code', keywords)
	name = self.extract_keyword('name', keywords)
	codebase = self.extract_keyword('codebase', keywords)
	align = self.extract_keyword('align', keywords, 'baseline')
	vspace = self.extract_keyword('vspace', keywords)
	hspace = self.extract_keyword('hspace', keywords)
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
	    name = value = None
	    for a, v in attrs:
		if a == 'name': name = v
		if a == 'value': value = v
	    if name is not None and value is not None:
		self.apploader.set_param(name, value)

    # New tag: <APP>

    def do_app(self, attrs):
	keywords = self.get_keywords(attrs)
	mod, cls, src = self.get_mod_class_src(keywords)
	if not (mod and cls): return
	width = self.extract_keyword('width', keywords, conv=string.atoi)
	height = self.extract_keyword('height', keywords, conv=string.atoi)
	menu = self.extract_keyword('menu', keywords)
	mod = mod + ".py"
	apploader = AppletLoader(self, code=mod, name=cls, codebase=src,
				 width=width, height=height, menu=menu,
				 reload=self.reload)
	if apploader.feasible():
	    for name, value in keywords.items():
		apploader.set_param(name, value)
	    apploader.go_for_it()
	else:
	    apploader.close()

    # Subroutines for <APP> tag parsing

    def get_keywords(self, attrs):
	keywords = {}
	for a, v in attrs:
	    keywords[a] = v
	return keywords

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

    # Handle HTML extensions

    def unknown_starttag(self, tag, attrs):
	function = self.app.find_html_start_extension(tag)
	if function:
	    function(self, attrs)

    def unknown_endtag(self, tag):
	function = self.app.find_html_end_extension(tag)
	if function:
	    function(self)
