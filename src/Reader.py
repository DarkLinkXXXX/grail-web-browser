"""Reader class -- helper to read documents asynchronously."""

import grailutil
import os
import sys
import string
import urlparse
from Tkinter import *
import tktools
from BaseReader import BaseReader
import regsub
import copy
import regex

# mailcap dictionary
caps = None


# If > 0, profile handle_data and print this many statistics lines
profiling = 0


class ParserWrapper:
    """Provides re-entrance protection around an arbitrary parser object.
    """
    def __init__(self, parser, viewer):
	self.__parser = parser
	self.__viewer = viewer
	self.__pendingdata = ''
	self.__closed = 0
	self.__closing = 0
	self.__level = 0

    def feed(self, data):
	self.__pendingdata = self.__pendingdata + data
	self.__level = self.__level + 1
	if self.__level == 1:
	    self.__viewer.unfreeze()
	    while self.__pendingdata:
		data = self.__pendingdata
		self.__pendingdata = ''
		self.__parser.feed(data)
	    if self.__closing and not self.__closed:
		self.__parser.close()
	    self.__viewer.freeze(1)
	self.__level = self.__level - 1

    def close(self):
	self.__closing = 1
	if not self.__level:
	    self.__viewer.unfreeze()
	    self.__parser.close()
	    self.__viewer.freeze()
	    self.__closed = 1


class Reader(BaseReader):

    """Helper class to read documents asynchronously.

    This is created by the Context.load() method and it is deleted
    when the document is fully read or when the user stops it.

    There should never be two Reader instances attached to the same
    Context instance, but if there were, the only harm done would be
    that their output would be merged in the context's viewer.

    """

    def __init__(self, context, url, method, params, show_source, reload,
		 data=None, scrollpos=None):

	self.last_context = context
	self.method = method
	self.params = copy.copy(params)
	self.show_source = show_source
	self.reload = reload
	self.data = data
	self.scrollpos = scrollpos

	self.save_file = None
	self.save_mailcap = None
	self.user_passwd = None
	self.maxrestarts = 10
	self.url = ''

	if url: self.restart(url)

    def restart(self, url):
	self.maxrestarts = self.maxrestarts - 1

	self.viewer = self.last_context.viewer
	self.app = self.last_context.app

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

	BaseReader.__init__(self, self.last_context, api)

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

    def handle_meta_prelim(self, errcode, errmsg, headers):
	self.last_context.set_headers(headers)
	if self.save_file:
	    if errcode != 200:
		self.stop()
		self.handle_error(errcode, errmsg, headers)
	    return

	if errcode == 204:
	    self.last_context.viewer.remove_temp_tag(histify=1)
	    self.app.global_history.remember_url(self.url)
	    self.stop()
	    return

	if errcode in (301, 302) and headers.has_key('location'):
	    url = headers['location']
	    if self.maxrestarts > 0:
		# remember the original click location
		self.app.global_history.remember_url(self.url)
		self.stop()
		# Always do a "GET" on the redirected URL
		self.method = 'GET'
		self.data = ""
		self.restart(url)
		return

	if errcode == 401:
	    if self.handle_auth_error(errcode, errmsg, headers):
		return

	return 1

    def handle_meta(self, errcode, errmsg, headers):
	if not self.handle_meta_prelim(errcode, errmsg, headers):
	    return

	if headers.has_key('content-type'):
	    content_type = headers['content-type']
	    if ';' in content_type:
		content_type = string.strip(
		    content_type[:string.index(content_type, ';')])
	    content_encoding = None
	else:
	    content_type, content_encoding = self.app.guess_type(self.url)
	if headers.has_key('content-encoding'):
	    content_encoding = headers['content-encoding']
	real_content_type = content_type or "unknown"
	real_content_encoding = content_encoding
	if content_encoding:
	    # XXX provisional hack -- change content type to octet stream
	    content_type = "application/octet-stream"
	    content_encoding = None
	if not content_type:
	    content_type = "text/plain"	# Last resort guess only

	istext = content_type and content_type[:5] == 'text/'
	if self.show_source and istext:
	    content_type = 'text/plain'
	parserclass = self.find_parser_extension(content_type)
	if not parserclass and istext:
	    if content_type != 'text/plain':
		# still need to check for text/plain
		parserclass = self.find_parser_extension('text/plain')
	    if not parserclass:
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
		    # remember the original click location
		    self.app.global_history.remember_url(self.url)
		    self.viewer.remove_temp_tag(histify=1)
		    return
	    # No relief from mailcap either.
	    # Ask the user whether and where to save it.
	    # Stop the transfer, and restart when we're ready.
	    context = self.last_context
	    # TBD: hack so that Context.rmreader() doesn't call
	    # Viewer.remove_temp_tag().  We'll call that later
	    # explicitly once we know whether the file has been saved
	    # or not.
	    context.source = None
	    self.stop()
	    context.message("Wait for save dialog...")
	    encoding = ''
	    if real_content_encoding:
		encoding = real_content_encoding + "ed "
		if encoding[:2] == "x-":
		    encoding = encoding[2:]
	    encoding_label = "MIME type: %s%s" % (encoding, real_content_type)
	    import FileDialog
	    fd = FileDialog.SaveFileDialog(context.root)
	    label = Label(fd.top, text=encoding_label)
	    label.pack(before=fd.filter)
	    # give it a default filename on which save within the
	    # current directory
	    urlasfile = string.splitfields(self.url, '/')
	    fn = fd.go(default=urlasfile[-1], key="save")
	    if not fn:
		# User canceled.  Stop the transfer.
		self.viewer.remove_temp_tag()
		return
	    self.viewer.remove_temp_tag(histify=1)
	    self.app.global_history.remember_url(self.url)
	    # Prepare to save.
	    # Always save in binary mode.
	    try:
		self.save_file = open(fn, "wb")
	    except IOError, msg:
		context.error_dialog(IOError, msg)
		return
	    TransferDisplay(context, fn, self)
	    return

	if headers.has_key('window-target'):
	    target = headers['window-target']
	    if target:
		context = self.context.find_window_target(target)
		if context is not self.context:
		    self.context.rmreader(self)
		    self.context = self.last_context = context
		    self.context.addreader(self)
		    self.viewer = self.context.viewer
	self.context.clear_reset()
	self.context.set_headers(headers)
	self.context.set_url(self.url)
	realparser = parserclass(self.viewer, reload=self.reload)
	self.parser = ParserWrapper(realparser, self.viewer)
	self.istext = istext
	self.last_was_cr = 0

    def handle_auth_error(self, errcode, errmsg, headers):
	# Return nonzero if handle_error() should return now
	if not headers.has_key('www-authenticate') \
	   or self.maxrestarts <= 0:
	    return

	cred_headers = {}
	for k in headers.keys():
	    cred_headers[string.lower(k)] = headers[k]
	cred_headers['request-uri'] = self.url

	if self.params.has_key('Authorization'):
	    self.app.auth.invalidate_credentials(cred_headers,
						 self.params['Authorization'])
	    return

	self.stop()
	credentials = self.app.auth.request_credentials(cred_headers)
	if credentials.has_key('Authorization'):
	    for k,v in credentials.items():
		self.params[k] = v
	    self.restart(self.url)
	    return 1
	# couldn't figure out scheme
	self.maxrestarts = 0
	self.restart(self.url)
	return

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

	try:
	    self.parser.feed(data)
	except IOError, msg:
	    self.stop()
	    try:
		errno, errmsg = msg
	    except:
		errno, errmsg = 0, str(msg)
	    self.handle_error(errno, errmsg, [])

    if profiling:
	bufsize = 8*1024
	_handle_data = handle_data
	def handle_data(self, data):
	    n = profiling
	    import profile, pstats
	    prof = profile.Profile()
	    prof.runcall(self._handle_data, data)
	    stats = pstats.Stats(prof)
	    stats.strip_dirs().sort_stats('time').print_stats(n)
	    stats.strip_dirs().sort_stats('cum').print_stats(n)

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
	    self.last_context.message("Saved.")
	    return
	import mailcap
	command, entry = mailcap.findmatch(
	    caps, self.save_content_type, 'view',
	    self.save_filename, self.save_plist)
	if not command:
	    command = self.save_mailcap
	self.last_context.message("Mailcap: %s" % command)
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
	app = self.context.app
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


class TransferDisplay:
    """A combined browser / viewer for asynchronous file transfers."""

    def __init__(self, old_context, filename, reader):
	url = old_context.get_baseurl()
	headers = old_context.get_headers()
	self.app = old_context.browser.app
	self.root = Toplevel(
	    old_context.browser.master, class_="GrailTransfer")
	import Context
	self.context = Context.SimpleContext(self, self)
	self.context._url = self.context._baseurl = url
	reader.last_context = self.context
	self.__filename = filename
	self.__reader = reader
	self.__save_file = reader.save_file
	reader.save_file = self
	if filename:
	    self.root.title("Grail: Downloading to "
			   + os.path.basename(filename))
	else:
	    self.root.title("Grail Download")
	self.root.iconname("Download")
	# icon set up
	iconxbm_file = grailutil.which('icon.xbm')
	if iconxbm_file:
	    try: self.root.iconbitmap('@' + iconxbm_file)
	    except TclError: pass
	#
	topfr = Frame(self.root)
	topfr.pack(expand=1, fill=BOTH, padx='1m', pady='1m')
	es, fs, ls = tktools.make_labeled_form_entry(
	    topfr, "Source:", takefocus=0, entrywidth=45, labelwidth=10)
	ed, fd, ld = tktools.make_labeled_form_entry(
	    topfr, "Destination:", takefocus=0, entrywidth=45, labelwidth=10)
	es.insert(END, url)
	ed.insert(END, filename)
	es.configure(state=DISABLED)
	ed.configure(state=DISABLED)
	fd.pack(pady='1m')
	Button(topfr, command=self.stop, text="Stop").pack()
	Frame(self.root, borderwidth=1, relief=SUNKEN, height=2
	      ).pack(fill=X)
	f = Frame(self.root)
	f.pack(fill=X)
	if headers.has_key('content-length'):
	    self.make_progress_bar(headers['content-length'], f)
	self.__status = Label(f, font=self.context.app.prefs.Get(
	    'presentation', 'message-font'), anchor=W)
	self.__status.pack(side=LEFT, fill=X)
	reader.restart(reader.url)
	reader.bufsize = 8096

    def message(self, string):
	pass

    __progbar = None
    def make_progress_bar(self, size, frame):
	try:
	    size = string.atoi(size)
	except ValueError:
	    return
	self.__maxsize = 1.0 * size	# make it a float for future calc.
	self.__progdesc = "%.1f%% of " + grailutil.nicebytes(size)
	# These frames must use the cnf={} approach to get the 1.4
	# Tkinter.Frame implementation to use the class setting.
	f = Frame(frame, relief=SUNKEN, borderwidth=1, background="powderblue",
		  height=10, width=162)
	f.pack(side=RIGHT, padx='1m')
	self.__progfr = f
	self.__progbar = Frame(f, width=1, background="darkblue",
			       height=string.atoi(f.cget('height')) - 2)
	self.__progbar.place(x=0, y=0)

    def stop(self):
	self.close()
	if os.path.isfile(self.__filename):
	    try: os.unlink(self.__filename)
	    except IOError, msg: self.context.error_dialog(IOError, msg)

    # file-like methods; these allow us to intercept the close() method
    # on the reader's save file object

    __datasize = 0
    def write(self, data):
	self.__save_file.write(data)
	datasize = self.__datasize = self.__datasize + len(data)
	if self.__progbar:
	    self.__progbar.config(
		width=max(1, int(datasize * 160 / self.__maxsize)))
	    desc = self.__progdesc % (100.0 * datasize / self.__maxsize)
	else:
	    desc = grailutil.nicebytes(datasize)
	self.__status["text"] = desc

    def close(self):
	self.__reader.stop()
	self.__save_file.close()
	self.__reader.save_file = self.__save_file
	self.__save_file = self.__reader = None
	self.root.destroy()
