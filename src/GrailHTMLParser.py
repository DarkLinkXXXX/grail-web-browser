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


class AppletHTMLParser(htmllib.HTMLParser):

    def __init__(self, viewer):
	self.viewer = viewer
	self.browser = self.viewer.browser
	self.tags = ()
	self.anchor = None
	htmllib.HTMLParser.__init__(self)

    def write_data(self, data):
##	s = `data`
##	if len(s) > 70: s = s[:30] + '...' + s[-30:]
##	print self.tags, s
	self.viewer.add_data(data, self.tags)

    def new_para(self):
	if self.para:
	    self.tags = (self.para,)
	    # XXX This hardcoded test is pathetic
	    if self.para in ('li1', 'li2', 'li3'):
		self.handle_data('* ') # XXX Should use real bullets
	else:
	    self.tags = ()

    def new_style(self):
	list = []
	if self.para: list.append(self.para)
	if self.styles: list = list + self.styles
	self.tags = tuple(filter(None, list))

    def anchor_bgn(self, href, name, type):
	self.anchor = href
	self.push_style(href and 'a' or None)
	self.push_style(href and '>' + href or None)
	self.push_style(name and '#' + name or None)

    def anchor_end(self):
	self.pop_style()
	self.pop_style()
	self.pop_style()
	self.anchor = None

    def handle_image(self, src, alt):
	image = self.browser.get_image(src)
	if not image:
	    self.handle_data(alt)
	    return
	label = AnchorLabel(self.viewer.text, image=image)
	if self.anchor:
	    label.setinfo(self.anchor, self.browser)
	if self.softspace:
	    self.handle_literal(' ')
	self.viewer.add_subwindow(label)

    def do_app(self, attrs):
	C, keywords = self.get_class(attrs)
	if not C: return
	if keywords.has_key('menu'):
	    menuname = keywords['menu']
	    del keywords['menu']
	    return self.applet_menu(C, keywords, menuname)
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
	mod = None
	cls = None
	src = ''
	reload = 0
	keywords = {}
	for a, v in attrs:
	    if a == 'module': mod = v
	    elif a == 'class': cls = v
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
	return self.get_class_proper(mod, cls, src, reload), keywords

    def get_class_proper(self, mod, cls, src, reload):
	if not (mod or cls):
	    print "*** No module or class specified"
	    return None
	if not mod: mod = cls
	if not cls: cls = mod
	modules = self.browser.app.modules
	if modules.has_key(mod): m = modules[mod]
	else: modules[mod] = m = imp.new_module(mod)
	try:
	    if reload: raise ''
	    return getattr(m, cls)
	except:
	    if src and src[-1] != '/': src = src + '/'
	    url = src + mod + '.py'
	    code = self.get_code(url)
	    if not code:
		del modules[mod]
		return None
	    try:
		exec code in m.__dict__
		return getattr(m, cls)
	    except:
		self.show_tb()
		del modules[mod]
		return None

    def get_code(self, src):
	url = urlparse.urljoin(self.browser.url, src)
	try:
	    fp = urllib.urlopen(url)
	    try:
		data = fp.read()
	    finally:
		fp.close()
	except IOError, msg:
	    print "*** Load of", `url`, "failed:", msg
	    return None
	try:
	    code = compile(data, url, 'exec')
	except SyntaxError:
	    self.show_tb()
	    return None
	return code

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
