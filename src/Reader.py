"""Reader class -- helper to read documents asynchronously."""


import urlparse
from Tkinter import *
from AppletHTMLParser import AppletHTMLParser
from BaseReader import BaseReader
import ProtocolAPI
import regsub
from copy import copy


# Buffer size for getdata()
BUFSIZE = 8*1024


class Reader(BaseReader):

    """Helper class to read documents asynchronously.

    This is created by the Browser.load() method and it is deleted
    when the document is fully read or when the user stops it.

    There should never be two Reader instances attached to the same
    Browser instance, but if there were, the only harm done would be
    that their output would be merged in the browser's viewer.

    """

    def __init__(self, browser, url, method, params, new, show_source, reload):

	self.last_browser = browser
	self.method = method
	self.params = params
	self.reload = reload
	self.new = new
	self.show_source = show_source

	self.restart(browser, url)

    def restart(self, browser, url):
	self.browser = browser
	self.url = url

	self.viewer = self.browser.viewer
	self.app = self.browser.app

	self.parser = None

	tuple = urlparse.urlparse(url)
	self.fragment = tuple[-1]
	tuple = tuple[:-1] + ("",)
	cleanurl = urlparse.urlunparse(tuple)

	if self.app:
	    api = self.app.open_url(cleanurl,
				    self.method, self.params, self.reload)
	else:
	    api = ProtocolAPI.protocol_access(cleanurl,
					      self.method, self.params)

	BaseReader.__init__(self, browser, api)

    def stop(self):
	BaseReader.stop(self)
	if self.parser:
	    parser = self.parser
	    self.parser = None
	    parser.close()

    def handle_error(self, errcode, errmsg, headers):
	if errcode == 204:
	    return
	if errcode in (301, 302) and headers.has_key('location'):
	    url = headers['location']
	    self.restart(self.last_browser, url)
	    return
	BaseReader.handle_error(self, errcode, errmsg, headers)

    def handle_meta(self, errcode, errmsg, headers):
	if headers.has_key('content-type'):
	    content_type = headers['content-type']
	else:
	    content_type = None
	if not content_type:
	    content_type, content_encoding = self.app.guess_type(self.url)
	else:
	    content_encoding = None
	if headers.has_key('content-encoding'):
	    content_encoding = headers['content-encoding']
	if content_encoding:
	    # XXX Should fix this
	    browser = self.browser
	    self.stop()
	    browser.error_dialog("Warning",
				 "unsupported content-encoding: %s"
				 % content_encoding)
	    return

	istext = content_type and content_type[:5] == 'text/'
	if self.show_source and istext:
	    content_type = 'text/plain'
	if content_type == 'text/html':
	    parserclass = AppletHTMLParser
	elif content_type == 'text/plain':
	    parserclass = TextParser
	else:
	    parserclass = self.find_parser_extension(content_type)
	    if not parserclass and istext:
		parserclass = TextParser

	if not parserclass:
	    # XXX Should save here
	    browser = self.browser
	    self.stop()
	    browser.error_dialog("Error",
				 "unsupported content-type: %s"
				 % content_type)
	    return

	self.parser = parserclass(self.viewer, reload=self.reload)
	self.istext = istext
	self.last_was_cr = 0
	self.browser.clear_reset(self.url, self.new)

    def handle_data(self, data):
	if self.istext:
	    if self.last_was_cr and data[0] == '\n':
		data = data[1:]
	    self.last_was_cr = data[-1:] == '\r'
	    if '\r' in data:
		if '\n' in data:
		    data = regsub.gsub('\r\n', '\n', data)
		if '\r' in data:
		    data = regsub.gsub('\r', '\n', data)

	self.viewer.unfreeze()
	self.parser.feed(data)
	self.viewer.freeze()

	if hasattr(self.parser, 'title'):
	    title = self.parser.title
	    if title and title != self.browser.title:
		self.browser.set_title(title)

    def handle_eof(self):
	if self.fragment:
	    self.viewer.scroll_to(self.fragment)

    def find_parser_extension(self, content_type):
	try:
	    [type, subtype] = string.splitfields(content_type, '/')
	except:
	    return None
	type = regsub.gsub("[^a-zA-Z0-9_]", "_", type)
	subtype = regsub.gsub("[^a-zA-Z0-9_]", "_", subtype)
	modname = type + "_" + subtype
	# XXX Some of this needs to be moved into the Application class
	home = getenv("HOME") or os.curdir
	graildir = getenv("GRAILDIR") or os.path.join(home, ".grail")
	mimetypesdir = os.path.join(graildir, "mimetypes")
	if mimetypesdir not in sys.path: sys.path.insert(0, mimetypesdir)
	# XXX Hack, hack, hack
	cmd = "import %s; parser = %s.parse_%s" % (modname, modname, modname)
	cmd2 = "import %s; parser = %s.parse_%s" % (type, type, type)
	try:
	    try:
		exec cmd
	    except ImportError:
		modname = type
		try:
		    exec cmd2
		except ImportError:
		    return None
	    return parser
	except:
	    self.app.exception_dialog("during import of %s" % modname)
	    return None


from formatter import AS_IS


class TextParser:

    title = ""

    def __init__(self, viewer, reload=0):
	self.viewer = viewer
	self.viewer.new_font((AS_IS, AS_IS, AS_IS, 1))

    def feed(self, data):
	self.viewer.send_literal_data(data)

    def close(self):
	pass
