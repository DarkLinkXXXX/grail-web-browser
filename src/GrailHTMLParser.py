"""HTML parser class with applet support."""


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

    # Override HTMLParser internal methods

    def anchor_bgn(self, href, name, type):
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
	    # Disgusting hack to tag the first character of the line
	    # so things like indents and centering work
	    data = ' '
	else:
	    data = ''
	self.handle_data(data)
	self.viewer.add_subwindow(w)

    # New tag: <CENTER> (for Amy)

    def start_center(self, attrs):
	self.formatter.push_style('center')

    def end_center(self):
	self.formatter.pop_style()

    # New tag: <APP>

    def do_app(self, attrs):
	C, keywords = self.get_class(attrs)
	if not C: return
	if keywords.has_key('menu'):
	    menuname = keywords['menu']
	    del keywords['menu']
	    return self.applet_menu(C, keywords, menuname)
	self.formatter.add_literal_data('')
	frame = AppletFrame(self.viewer.text, self)
	try:
	    w = apply(C, (frame,), keywords)
	except:
	    self.show_tb()
	    frame.destroy()
	    return
	self.add_subwindow(frame)

    def applet_menu(self, C, keywords, menuname):
	browser = self.browser
	menubutton = Menubutton(browser.mbar, text=menuname)
	menubutton.pack(side='left')
	menu = AppletMenu(menubutton, self)
	menubutton['menu'] = menu
	try:
	    w = apply(C, (menu,), keywords)
	except:
	    self.show_tb()
	    menubutton.destroy()
	    return
	browser.user_menus.append(menubutton)

    def get_class(self, attrs):
	cls = None
	src = ''
	keywords = {}
	for a, v in attrs:
	    if a == 'class': cls = v
	    elif a == 'src': src = v
	    else:
		try: v = string.atoi(v, 0)
		except string.atoi_error:
		    try: v = string.atol(v, 0)
		    except string.atol_error:
			try: v = string.atof(v)
			except string.atof_error: pass
		keywords[a] = v
	if not cls:
	    print "*** APP tag has no CLASS attribute"
	    return
	if '.' in cls:
	    i = string.rfind(cls, '.')
	    mod = cls[:i]
	    cls = cls[i+1:]
	else:
	    mod = cls
	try:
	    return self.get_class_proper(mod, cls, src), keywords
	except:
	    self.show_tb()
	    return None, keywords

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
