"""Implement applet loading, possibly asynchronous."""

import os
import regex
import string
import urlparse
from Tkinter import *
from BaseReader import BaseReader


# Pattern for valid CODE attribute; group(2) extracts module name
codeprog = regex.compile('^\(.*/\)?\([_a-zA-Z][_a-zA-Z0-9]*\)\.py$')


class AppletLoader:

    """Stores semantic information about an applet-to-be.

    This class stores the information gathered from parsing an <APP>
    <APPLET> or <INSERT> tag for an applet, and from the <PARAM> tags
    present within the body of <APPLET> or <INSERT>.  It doesn't do
    any of the parsing itself, but it stores the information gathered
    by the parser.  When the time is ready to instantiate the applet,
    it will do so, either immediately (if its module has laready been
    loaded), or after loading the module asynchronously.

    """

    def __init__(self, parser, name=None, code=None, codebase=None,
		 width=None, height=None, vspace=None, hspace=None,
		 align=None,
		 menu=None, reload=0):
	"""Store the essential data (from the app or applet tag)"""
	self.parser = parser
	self.viewer = self.parser.viewer
	self.browser = self.parser.browser
	self.app = self.parser.app

	self.name = name
	self.code = code
	self.codebase = codebase
	self.width = width
	self.height = height
	self.vspace = vspace
	self.hspace = hspace
	self.align = align
	self.menu = menu
	self.reload = reload
	
	self.params = {}

	self.modname = None
	self.codeurl = None

	self.parent = None
	self.module = None
	self.klass = None
	self.instance = None

    def __del__(self):
	"""Attempt to close() once more."""
	self.close()

    def close(self):
	"""Delete all references to external objects."""
	self.parser = self.viewer = self.browser = self.app = None
	self.params = {}
	self.modname = self.codeurl = None
	self.parent = self.module = self.klass = self.instance = None

    def feasible(self):
	"""Test whether we should try load the applet."""
	return self.code and codeprog.match(self.code) == len(self.code)

    def set_param(self, name, value):
	"""Set the value for a named parameter for the widget."""
	try:
	    value = string.atoi(value, 0)
	except string.atoi_error:
	    try:
		value = string.atol(value, 0)
	    except string.atol_error:
		try:
		    value = string.atof(value)
		except string.atof_error:
		    pass
	self.params[name] = value

    def go_for_it(self):
	"""Import the module and instantiate the class, maybe async.

	This is synchronous if the module has already been loaded or
	if it will be loaded from a local file; it is asynchronous if
	the module has to be loaded from a remote site.  Errors in
	this stage are reported via the standard error dialog.

	"""
	try:
	    self._go_for_it()
	except:
	    self.show_tb()
	    self.close()

    def _go_for_it(self):
	self.get_defaults()
	self.module = self.get_easy_module(self.modname)
	if self.module:
	    # Synchronous loading
	    self.klass = getattr(self.module, self.name)
	    self.parent = self.make_parent()
	    self.instance = apply(self.klass, (self.parent,),
				  self.params)
	else:
	    # Asynchronous loading
	    self.parent = self.make_parent()
	    api = self.app.open_url(self.codeurl, 'GET', {}, self.reload)
	    ModuleReader(self.browser, api, self)

    def make_parent(self):
	"""Return a widget that will be the applet's parent.

	This is either a menu or a frame subwindow of the text widget.

	"""
	if self.menu:
	    browser = self.browser
	    menubutton = Menubutton(browser.mbar, text=self.menu)
	    menubutton.pack(side=LEFT)
	    menu = AppletMenu(menubutton, self)
	    menubutton['menu'] = menu
	    browser.user_menus.append(menubutton)
	    parent = menu
	else:
	    bg = self.viewer.text['background']
	    frame = AppletFrame(self.viewer.text, self, background=bg)
	    if self.width: frame.config(width=self.width)
	    if self.height: frame.config(height=self.height)
	    self.parser.add_subwindow(frame)
	    parent = frame
	return parent			#  FLD:  made to work in either case

    def load_it_now(self):
	"""Invoked by ModuleReader when it is done, to create the applet."""
	try:
	    self._load_it_now()
	except:
	    self.show_tb()
	    self.close()

    def _load_it_now(self):
	"""Internal -- load_it_now(), without the try/except clause."""
	mod = self.modname
	rexec = self.app.rexec
	rexec.reset_urlpath()
	rexec.set_urlpath(self.codeurl)
	rexec.loader.load_module = self.load_module
	try:
	    if self.reload and rexec.modules.has_key(mod) and \
	       mod not in self.parser.loaded:
		# XXX Hack, hack
		msg, crs = self.browser.message("Reloading module " + mod)
		self.module = rexec.modules[mod]
		rexec.r_reload(self.module)
	    else:
		msg, crs = self.browser.message("Loading module " + mod)
		self.module = rexec.r_import(mod)
	finally:
	    del rexec.loader.load_module
	self.parser.loaded.append(mod)
	self.browser.message(msg, crs)
	self.klass = getattr(self.module, self.name)
	self.instance = apply(self.klass, (self.parent,), self.params)

    def get_defaults(self):
	"""Internal -- calculate defaults for applet parameters."""
	if codeprog.match(self.code) >= 0:
	    self.modname = codeprog.group(2)
	else:
	    self.modname = "?" # Shouldn't happen
	if not self.name:
	    self.name = self.modname
	codeurl = self.browser.baseurl()
	if self.codebase:
	    codeurl = urlparse.urljoin(codeurl, self.codebase)
	codeurl = urlparse.urljoin(codeurl, self.code)
	self.codeurl = codeurl

    def get_easy_module(self, mod):
	"""Internal -- import a module if it can be done locally."""
	m = None
	if not self.reload:
	    m = self.mod_is_loaded(mod)
	    if not m:
		stuff = self.mod_is_local(mod)
		if stuff:
		    m = self.load_module(mod, stuff)
	else:
	    stuff = self.mod_is_local(mod)
	    if stuff:
		if mod in self.parser.loaded:
		    file = stuff[0]
		    if file and hasattr(file, 'close'):
			file.close()
		    m = self.mod_is_loaded(mod)
		else:
		    self.parser.loaded.append(mod)
		    m = self.load_module(mod, stuff)
	return m

    def mod_is_loaded(self, mod):
	"""Internal -- check whether a module has already been loaded."""
	rexec = self.app.rexec
	try:
	    return rexec.modules[mod]
	except KeyError:
	    return None

    def mod_is_local(self, mod):
	"""Internal -- check whether a module can be found locally."""
	rexec = self.app.rexec
	path = rexec.get_url_free_path()
	return rexec.loader.find_module(mod, path)

    def load_module(self, mod, stuff):
	"""Internal -- load a module given the imp.find_module() stuff."""
	rexec = self.app.rexec
	rexec.reset_urlpath()
	# XXX Duplicate stuff from rexec.RModuleLoader.load_module()
	# and even from ihooks.FancyModuleLoader.load_module().
	# This is needed to pass a copy of the source to linecace.
        file, filename, info = stuff
	(suff, mode, type) = info
	import imp
	if type == imp.PY_SOURCE:
	    import linecache
	    lines = file.readlines()
	    data = string.joinfields(lines, '')
	    linecache.cache[filename] = (len(data), 0, lines, filename)
	    code = compile(data, filename, 'exec')
	    m = self.app.rexec.hooks.add_module(mod)
	    m.__filename__ = filename
	    exec code in m.__dict__
	else:
	    raise ImportError, "Unsupported module type: %s" % `filename`
        return m

    def show_tb(self):
	"""Internal -- post an exception dialog (via the app)."""
	self.app.exception_dialog("during applet loading")


class ModuleReader(BaseReader):

    """Load an applet, asynchronously.

    First load an applet's source module into the cache.  Once it's
    done, invoke the standard mechanism to actually load the module.
    This will find the source ready for it in the cache.

    """

    def __init__(self, browser, api, apploader):
	self.apploader = apploader
	BaseReader.__init__(self, browser, api)

    def handle_error(self, errno, errmsg, headers):
	self.apploader.close()
	self.apploader = None
	BaseReader.handle_error(self, errno, errmsg, headers)

    def handle_eof(self):
	apploader = self.apploader
	self.apploader = None
	apploader.load_it_now()


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
