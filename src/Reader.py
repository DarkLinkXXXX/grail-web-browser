"""Reader class -- helper to read documents asynchronously."""


import urlparse
from Tkinter import *
from AppletHTMLParser import AppletHTMLParser
import ProtocolAPI
import regsub
from copy import copy


# API reading stages
META, DATA, DONE = 'META', 'DATA', 'DONE'


# Buffer size for getdata()
BUFSIZE = 8*1024


class Reader:

    """Helper class to read documents asynchronously.

    This is created by the Browser.load() method and it is deleted
    when the document is fully read or when the user stops it.

    There should never be two Reader instances attached to the same
    Browser instance, but if there were, the only harm done would be
    that their output would be merged in the browser's viewer.

    """

    def __init__(self, browser, url, method, params, new, show_source, reload):
	self.browser = browser
	self.url = url
	self.method = method
	self.params = params
	self.new = new
	self.show_source = show_source
	self.reload = reload

	self.viewer = self.browser.viewer
	self.app = self.browser.app
	self.root = self.browser.root
	self.tk = self.root.tk

	self.api = None
	self.stage = DONE
	self.fno = -1
	self.parser = None

	tuple = urlparse.urlparse(url)
	self.fragment = tuple[-1]
	tuple = tuple[:-1] + ("",)
	cleanurl = urlparse.urlunparse(tuple)
	if self.app:
	    self.api = self.app.open_url(cleanurl, 'GET', params, reload)
	else:
	    self.api = ProtocolAPI.protocol_access(cleanurl, 'GET', params)
	self.browser.allowstop()
	self.stage = META
	self.fno = self.api.fileno()
	if self.fno >= 0:
	    self.root.tk.createfilehandler(
		self.fno, tkinter.READABLE, self.checkapi)
	else:
	    self.checkapi_regular()

    def checkapi_regular(self):
	self.checkapi()
	if self.stage in (META, DATA):
	    self.root.after(100, self.checkapi_regular)

    def checkapi(self, *args):
	if self.stage == META:
	    message, ready = self.api.pollmeta()
	    self.message(message)
	    if ready:
		self.getapimeta()
	elif self.stage == DATA:
	    message, ready = self.api.polldata()
	    self.message(message)
	    if ready:
		self.getapidata()

    def getapimeta(self):
	self.message("Getting meta-data for %s" % self.url)
	errcode, errmsg, headers = self.api.getmeta()
	self.stage = DATA
	if errcode != 200:
	    if errcode == 204:
		self.stage == DONE
		self.stop("No content.")
		return
	    if errcode in (301, 302) and headers.has_key('location'):
		url = headers['location']
		if self.fno >= 0:
		    self.root.tk.deletefilehandler(self.fno)
		self.api.close()
		self.__init__(self.browser, url, self.method, self.params,
			      self.new, self.show_source, self.reload)
		return
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
	    self.stop("Unknown encoding.")
	    self.browser.error_dialog("Warning",
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
	    self.stop("Too stupid.")
	    self.browser.error_dialog("Error",
				      "unsupported content-type: %s"
				      % content_type)
	    return

	self.parser = parserclass(self.viewer, reload=self.reload)
	self.istext = istext
	self.last_was_cr = 0
	self.browser.clear_reset(self.url, self.new)

    def getapidata(self):
	buf = self.api.getdata(BUFSIZE)
	if not buf:
	    self.stop("Done.")
	    if self.fragment:
		self.viewer.scroll_to(self.fragment)
	    return

	if self.istext:
	    if self.last_was_cr and buf[0] == '\n':
		buf = buf[1:]
	    self.last_was_cr = buf[-1:] == '\r'
	    if '\r' in buf:
		if '\n' in buf:
		    buf = regsub.gsub('\r\n', '\n', buf)
		if '\r' in buf:
		    buf = regsub.gsub('\r', '\n', buf)

	self.viewer.unfreeze()
	self.parser.feed(buf)
	self.viewer.freeze()

	if self.parser and hasattr(self.parser, 'title'):
	    title = self.parser.title
	    if title and title != self.browser.title:
		self.browser.set_title(title)

    def stop(self, msg=None):
	api = self.api
	if api:
	    self.browser.clearstop()
	    self.message("Stopping...")
	    self.browser.rmreader(self)
	    parser = self.parser
	    fno = self.fno
	    self.api = None
	    self.stage = DONE
	    self.parser = None
	    self.fno = -1
	    if parser: parser.close()
	    if fno >= 0:
		self.root.tk.deletefilehandler(fno)
	    api.close()
	    self.message(msg)

    def message(self, msg=None):
	self.browser.message(msg)

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
