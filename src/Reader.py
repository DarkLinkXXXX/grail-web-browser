"""Reader class -- helper to read documents asynchronously."""


from grailutil import *
import os
import sys
import string
import urlparse
from Tkinter import *
import tktools
from AppletHTMLParser import AppletHTMLParser
from BaseReader import BaseReader
import regsub
from copy import copy


# mailcap dictionary
caps = None


class Reader(BaseReader):

    """Helper class to read documents asynchronously.

    This is created by the Browser.load() method and it is deleted
    when the document is fully read or when the user stops it.

    There should never be two Reader instances attached to the same
    Browser instance, but if there were, the only harm done would be
    that their output would be merged in the browser's viewer.

    """

    def __init__(self, browser, url, method, params, new, show_source, reload,
		 data=None, scrollpos=None):

	self.last_browser = browser
	self.method = method
	self.params = params
	self.new = new
	self.show_source = show_source
	self.reload = reload
	self.data = data
	self.scrollpos = scrollpos

	self.save_file = None
	self.save_mailcap = None
	self.user_passwd = None
	self.maxrestarts = 10
	self.url = ''

	self.restart(url)

    def restart(self, url):
	self.maxrestarts = self.maxrestarts - 1

	self.viewer = self.last_browser.viewer
	self.app = self.last_browser.app

	self.parser = None

	tuple = urlparse.urlparse(url)
	# it's possible that the url send in a 301 or 302 error is a
	# relative URL.  if there's no scheme or netloc in the
	# returned tuple, try joining the URL with the previous URL
	# and retry parsing it.
	if not (tuple[0] and tuple[1]):
	    url = urlparse.urljoin(self.url, url)
	    tuple = urlparse.urlparse(url)
	self.url = url

	self.fragment = tuple[-1]
	tuple = tuple[:-1] + ("",)
	if self.user_passwd:
	    netloc = tuple[1]
	    i = string.find(netloc, '@')
	    if i >= 0: netloc = netloc[i+1:]
	    netloc = self.user_passwd + '@' + netloc
	    tuple = (tuple[0], netloc) + tuple[2:]
	realurl = urlparse.urlunparse(tuple)

	if self.app:
	    api = self.app.open_url(realurl,
				    self.method, self.params, self.reload,
				    data=self.data)
	else:
	    import protocols
	    api = protocols.protocol_access(realurl,
					    self.method, self.params,
					    data=self.data)

	BaseReader.__init__(self, self.last_browser, api)

    def stop(self):
	BaseReader.stop(self)
	if self.parser:
	    parser = self.parser
	    self.parser = None
	    parser.close()

    def handle_error(self, errcode, errmsg, headers):
	if self.save_file:
	    self.save_file.close()
	    self.save_file = None
	    if self.save_mailcap:
		try:
		    os.unlink(self.save_filename)
		except os.error:
		    pass
	BaseReader.handle_error(self, errcode, errmsg, headers)

    def handle_meta(self, errcode, errmsg, headers):
	if self.save_file:
	    if errcode != 200:
		self.stop()
		self.handle_error(errcode, errmsg, headers)
	    return

	if errcode == 204:
	    self.stop()
	    return

	if errcode in (301, 302) and headers.has_key('location'):
	    url = headers['location']
	    if self.maxrestarts > 0:
		self.stop()
		self.restart(url)
		return

	if errcode == 401:
	    if self.handle_auth_error(errcode, errmsg, headers):
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
	    # XXX provisional hack -- change content type to octet stream
	    content_type = "application/octet-stream"
	    content_encoding = None

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
	    # Don't know how to display this.
	    # First consult mailcap.
	    import mailcap
	    global caps
	    if not caps:
		caps = mailcap.getcaps()
	    if caps:
		plist = [] # XXX Should be taken from Content-type header
		command, entry = mailcap.findmatch(
		    caps, content_type, 'view', "/dev/null", plist)
		if command:
		    # Retrieve to temporary file.
		    import tempfile
		    self.save_mailcap = command
		    self.save_filename = tempfile.mktemp()
		    self.save_content_type = content_type
		    self.save_plist = plist
		    self.save_file = open(self.save_filename, "wb")
		    return
	    # No relief from mailcap either.
	    # Ask the user whether and where to save it.
	    # Stop the transfer, and restart when we're ready.
	    browser = self.last_browser
	    self.stop()
	    browser.message("Wait for save dialog...")
	    import FileDialog
	    fd = FileDialog.SaveFileDialog(browser.root)
	    # give it a default filename on which save within the
	    # current directory
	    urlasfile = string.splitfields(self.url, '/')
	    fn = fd.go(default=urlasfile[-1])
	    if not fn:
		# User canceled.  Stop the transfer.
		return
	    # Prepare to save.
	    # Always save in binary mode.
	    try:
		self.save_file = open(fn, "wb")
	    except IOError, msg:
		browser.error_dialog(IOError, msg)
		return
	    self.restart(self.url)
	    browser.message("Saving to %s" % fn)
	    return

	self.browser.clear_reset(self.url, self.new)
	self.parser = parserclass(self.viewer, reload=self.reload)
	self.istext = istext
	self.last_was_cr = 0

    def handle_auth_error(self, errcode, errmsg, headers):
	# Return nonzero if handle_error() should return now
	if not headers.has_key('www-authenticate') or self.maxrestarts <= 0:
	    return
	challenge = headers['www-authenticate']
	# <authscheme> realm="<value>" [, <param>="<value>"] ...
	parts = string.splitfields(challenge, ',')
	p = parts[0]
	i = string.find(p, '=')
	if i < 0: return
	key, value = p[:i], p[i+1:]
	keyparts = string.split(string.lower(key))
	if not(len(keyparts) == 2 and keyparts[1] == 'realm'): return
	authscheme = keyparts[0]
	value = string.strip(value)
	if len(value) >= 2 and value[0] == value[-1] and value[0] in '\'"':
	    value = value[1:-1]
	self.stop()
	self.user_passwd = self.get_user_passwd(authscheme, value)
	if not self.user_passwd:
	    self.maxrestarts = 0
	self.restart(self.url)
	return 1

    def get_user_passwd(self, authscheme, realmvalue):
	if authscheme != "basic": return None
	netloc = urlparse.urlparse(self.url)[1]
	i = string.find(netloc, '@')
	if i >= 0: netloc = netloc[i+1:]
	i = string.find(netloc, ':')
	if i >= 0: netloc = netloc[:i]
	key = (netloc, realmvalue)
	browser = self.last_browser
	app = browser.app
	if app.login_cache.has_key(key):
	    if self.user_passwd:
		del app.login_cache[key]
	    else:
		return app.login_cache[key]
	login = LoginDialog(browser.root, netloc, realmvalue)
	user_passwd = login.go()
	if user_passwd:
	    app.login_cache[key] = user_passwd
	return user_passwd

    def handle_data(self, data):
	if self.save_file:
	    self.save_file.write(data)
	    return
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
	    if title:
		self.browser.set_title(title)

    def handle_eof(self):
	if not self.save_file:
	    if self.fragment:
		self.viewer.scroll_to(self.fragment)
	    elif self.scrollpos:
		self.viewer.scroll_to_position(self.scrollpos)
	    return
	self.save_file.close()
	self.save_file = None
	if not self.save_mailcap:
	    self.last_browser.message("Saved.")
	    return
	import mailcap
	command, entry = mailcap.findmatch(
	    caps, self.save_content_type, 'view',
	    self.save_filename, self.save_plist)
	if not command:
	    command = self.save_mailcap
	self.last_browser.message("Mailcap: %s" % command)
	command = "(%s; rm -f %s)&" % (command, self.save_filename)
	sts = os.system(command)
	if sts:
	    print "Exit status", sts, "from command", command

    def find_parser_extension(self, content_type):
	try:
	    [type, subtype] = string.splitfields(content_type, '/')
	except:
	    return None
	type = regsub.gsub("[^a-zA-Z0-9_]", "_", type)
	subtype = regsub.gsub("[^a-zA-Z0-9_]", "_", subtype)
	app = self.browser.app
	for modname in (type + "_" + subtype, type):
	    m = app.find_extension('filetypes', modname)
	    if m:
		pname = "parse_" + modname
		if hasattr(m, pname):
		    return getattr(m, pname)
	return None


class LoginDialog:

    def __init__(self, master, netloc, realmvalue):
	self.root = tktools.make_toplevel(master,
					  title="Authentication Dialog")
	self.prompt = Label(self.root,
			    text="Enter user authentication\nfor %s on %s" %
			    (realmvalue, netloc))
	self.prompt.pack(side=TOP)
	self.user_entry, dummy = tktools.make_form_entry(self.root, "User:")
	self.user_entry.focus_set()
	self.user_entry.bind('<Return>', self.user_return_event)
	self.passwd_entry, dummy = \
			   tktools.make_form_entry(self.root, "Password:")
	self.passwd_entry.config(show="*")
	self.passwd_entry.bind('<Return>', self.ok_command)
	self.ok_button = Button(self.root, text="OK", command=self.ok_command)
	self.ok_button.pack(side=LEFT)
	self.cancel_button = Button(self.root, text="Cancel",
				    command=self.cancel_command)
	self.cancel_button.pack(side=RIGHT)

	self.user_passwd = None

	tktools.set_transient(self.root, master)

	self.root.grab_set()

    def go(self):
	try:
	    self.root.mainloop()
	except SystemExit:
	    return self.user_passwd

    def user_return_event(self, event):
	self.passwd_entry.focus_set()

    def ok_command(self, event=None):
	user = string.strip(self.user_entry.get())
	passwd = string.strip(self.passwd_entry.get())
	if not user:
	    self.root.bell()
	    return
	self.user_passwd = user + ':' + passwd
	self.goaway()

    def cancel_command(self):
	self.user_passwd = None
	self.goaway()

    def goaway(self):
	self.root.destroy()
	raise SystemExit


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
