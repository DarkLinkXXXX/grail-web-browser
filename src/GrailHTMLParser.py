"""HTML parser class with applet support."""


# XXX To do:
# - <HR> and <H1> don't always start a new paragraph (e.g. after an image)
# - rework interaction between font choices
#   - basically, para styles like <h1> or <pre> choose a font set,
#     and char styles like <i> or <b> or <code> choose a font.
#     This can get tricky when you combine <i>, <b> and <code> inside <h1> ...
#
# - merge app and usermenu tags
# - security for applets based on rexec
# - remote import for applets
# - garbage collect applets environments
# 
# Maybe later...
# - real list bullets
# - <CENTER>
# - imagemaps
# - <FORM>


from Tkinter import *
import htmllib
import imp
import traceback
import urlparse
import urllib
import string
import tktools
import formatter


class AppletHTMLParser(htmllib.HTMLParser):

    def __init__(self, viewer):
	self.viewer = viewer
	self.formatter = formatter.AbstractFormatter(self.viewer)
	htmllib.HTMLParser.__init__(self, self.formatter)
	self.browser = self.viewer.browser
	self.style_stack = []

    # Override HTMLParser internal methods

    def anchor_bgn(self, href, name, type):
	self.anchor = href
	self.formatter.push_style(href and 'a' or None)
	self.formatter.push_style(href and '>' + href or None)
	self.formatter.push_style(name and '#' + name or None)

    def anchor_end(self):
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.formatter.pop_style()
	self.anchor = None

    def handle_image(self, src, alt):
	image = self.browser.get_image(src)
	if not image:
	    self.handle_data(alt)
	    return
	self.formatter.add_literal_data('')
	label = AnchorLabel(self.viewer.text, image=image)
	if self.anchor:
	    label.setinfo(self.anchor, self.browser)
	self.viewer.add_subwindow(label)

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
	self.viewer.add_subwindow(frame)

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
	reload = 0
	keywords = {}
	for a, v in attrs:
	    if a == 'class': cls = v
	    elif a == 'src': src = v
	    elif a == 'reload': reload = tktools.boolean(v)
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
	    return self.get_class_proper(mod, cls, src, reload), keywords
	except:
	    self.show_tb()
	    return None, keywords

    def get_class_proper(self, mod, cls, src, reload):
	rexec = self.browser.app.rexec
	rexec.reset_urlpath()
	url = urlparse.urljoin(self.browser.url, src or '.')
	rexec.set_urlpath(url)
	msg, crs = self.viewer.browser.message("Loading module " + mod)
	m = rexec.r_import(mod)
	self.viewer.browser.message(msg, crs)
	return getattr(m, cls)

    def show_tb(self):
	print "-"*40
	print "Exception during extension loading:"
	traceback.print_exc()
	print "-"*40


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


class AnchorLabel(Label):

    def setinfo(self, url, browser):
	self.url = url
	self.browser = browser
	self.bind('<ButtonRelease-1>', self.follow)
	self.bind('<Enter>', self.enter)
	self.bind('<Leave>', self.leave)
	self.config(borderwidth=2, background='blue')

    def enter(self, event):
	self.browser.enter(self.url)

    def leave(self, event):
	self.browser.leave()

    def follow(self, event):
	self.browser.follow(self.url)
