"""HTML parser class with support for applets and other Grail features."""


from Tkinter import *
import htmllib
import imp
import urlparse
import urllib
import string
import tktools
import formatter


class AppletHTMLParser(htmllib.HTMLParser):

    def __init__(self, viewer, reload=0):
	self.viewer = viewer
	self.reload = reload
	self.app = self.viewer.browser.app
	self.formatter = formatter.AbstractFormatter(self.viewer)
	htmllib.HTMLParser.__init__(self, self.formatter)
	self.browser = self.viewer.browser
	self.style_stack = []
	self.loaded = []
	self.applets = []

    def close(self):
	for frame, keywords in self.applets:
	    C = self.get_class(keywords)
	    if frame == 'menu':
		self.menu_applet(C, keywords)
	    else:
		self.subwindow_applet(frame, C, keywords)
	htmllib.HTMLParser.close(self)

    # Override HTMLParser internal methods

    def anchor_bgn(self, href, name, type):
	self.formatter.flush_softspace()
	self.anchor = href
	atag = href and 'a' or None
	utag = href and '>' + href or None
	ntag = name and '#' + name or None
	self.formatter.push_style(atag)
	self.formatter.push_style(utag)
	self.formatter.push_style(ntag)
	if utag:
	    self.viewer.bind_anchors(utag)

    def anchor_end(self):
	self.formatter.flush_softspace()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.anchor = None

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
	    self.formatter.add_literal_data("\240") # Non-breaking space
	self.viewer.add_subwindow(w)

    # New tag: <CENTER> (for Amy)

    def start_center(self, attrs):
	self.formatter.push_style('center')

    def end_center(self):
	self.formatter.pop_style()

    # New tag: <APP>

    def do_app(self, attrs):
	keywords = self.get_keywords(attrs)
	if keywords.has_key('menu'):
	    entry = ('menu', keywords)
	else:
	    frame = AppletFrame(self.viewer.text, self)
	    self.add_subwindow(frame)
	    entry = (frame, keywords)
	self.applets.append(entry)

    def get_keywords(self, attrs):
	keywords = {}
	for a, v in attrs:
	    try: v = string.atoi(v, 0)
	    except string.atoi_error:
		try: v = string.atol(v, 0)
		except string.atol_error:
		    try: v = string.atof(v)
		    except string.atof_error: pass
	    keywords[a] = v
	return keywords

    # Stuff for applet creation -- now called from close()

    def menu_applet(self, C, keywords):
	menuname = keywords['menu']
	del keywords['menu']
	browser = self.browser
	menubutton = Menubutton(browser.mbar, text=menuname)
	menubutton.pack(side=LEFT)
	menu = AppletMenu(menubutton, self)
	menubutton['menu'] = menu
	try:
	    w = apply(C, (menu,), keywords)
	except:
	    self.show_tb()
	    menubutton.destroy()
	    return
	browser.user_menus.append(menubutton)

    def subwindow_applet(self, frame, C, keywords):
	try:
	    w = apply(C, (frame,), keywords)
	except:
	    self.show_tb()
	    frame.destroy()
	    return

    def get_class(self, keywords):
	cls = None
	src = ''
	if keywords.has_key('class'):
	    cls = keywords['class']
	    del keywords['class']
	if keywords.has_key('src'):
	    src = keywords['src']
	    del keywords['src']
	if not cls:
	    print "*** APP tag has no CLASS attribute"
	    return None
	if '.' in cls:
	    i = string.rfind(cls, '.')
	    mod = cls[:i]
	    cls = cls[i+1:]
	else:
	    mod = cls
	try:
	    return self.get_class_proper(mod, cls, src)
	except:
	    self.show_tb()
	    return None

    def get_class_proper(self, mod, cls, src):
	rexec = self.browser.app.rexec
	rexec.reset_urlpath()
	url = urlparse.urljoin(self.browser.url, src or '.')
	rexec.set_urlpath(url)
	if self.reload and rexec.modules.has_key(mod) and \
	   mod not in self.loaded:
	    # XXX Hack, hack
	    msg, crs = self.viewer.browser.message("Reloading module " + mod)
	    m = rexec.modules[mod]
	    rexec.r_reload(m)
	else:
	    msg, crs = self.viewer.browser.message("Loading module " + mod)
	    m = rexec.r_import(mod)
	self.loaded.append(mod)
	self.viewer.browser.message(msg, crs)
	return getattr(m, cls)

    def show_tb(self):
	self.app.exception_dialog("during applet loading")

    # Handle HTML extensions

    def unknown_starttag(self, tag, attrs):
	app = self.viewer.browser.app
	function = app.find_html_start_extension(tag)
	if function:
	    function(self, attrs)

    def unknown_endtag(self, tag):
	app = self.viewer.browser.app
	function = app.find_html_end_extension(tag)
	if function:
	    function(self)


class AppletMagic:

    def __init__(self, parser):
	self.grail_parser = parser
	self.grail_viewer = self.grail_browser = self.grail_app = None
	if parser:
	    self.grail_viewer = viewer = parser.viewer
	    if viewer:
		self.grail_browser = browser = viewer.browser
		if browser:
		    self.grail_app = app = browser.app


class AppletFrame(Frame, AppletMagic):

    def __init__(self, master, parser=None, cnf={}, **kw):
	apply(Frame.__init__, (self, master, cnf), kw)
	AppletMagic.__init__(self, parser)


class AppletMenu(Menu, AppletMagic):

    def __init__(self, master, parser=None, cnf={}, **kw):
	apply(Menu.__init__, (self, master, cnf), kw)
	AppletMagic.__init__(self, parser)
