# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

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
import time

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

	# Check first to see if the previous Context has any protocol handlers
	api = self.last_context.get_local_api(realurl, self.method,
					      self.params)
	if not api:
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
	app = self.context.app
	modname, mod = app.find_type_extension('filetypes', content_type)
	if modname:
	    pname = "parse_" + modname
	    if hasattr(mod, pname):
		return getattr(mod, pname)
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


# This constant is the minimum interval between the times we force the
# display to be updated during an asynchronous download.  This makes the
# display update less "choppy" over fast links, where the display might
# not get updated because another socket event occurs before re-entering
# the main loop.  See TransferDisplay.write() for use.
#
TRANSFER_STATUS_UPDATE_PERIOD = 0.5

DARK_BLUE = "#00008b"
LIGHT_BLUE = "#b0e0e6"


class TransferDisplay:
    """A combined browser / viewer for asynchronous file transfers."""

    def __init__(self, old_context, filename, reader, restart=1):
	url = old_context.get_url()
	headers = old_context.get_headers()
	self.app = old_context.browser.app
	self.root = tktools.make_toplevel(
	    old_context.browser.master, class_="GrailTransfer")
	self.root.protocol("WM_DELETE_WINDOW", self.stop)
	import Context
	self.context = Context.SimpleContext(self, self)
	self.context._url = self.context._baseurl = url
	reader.last_context = self.context
	self.__filename = filename
	self.__reader = reader
	self.__save_file = reader.save_file
	reader.save_file = self
	if filename:
	    self.root.title("Grail: Downloading "
			   + os.path.basename(filename))
	else:
	    self.root.title("Grail Download")
	self.root.iconname("Download")
	#
	self.content_length = None
	if headers.has_key('content-length'):
	    self.content_length = string.atoi(headers['content-length'])
	self.create_widgets(url, filename, self.content_length)
	#
	if restart:
	    reader.restart(reader.url)
	reader.bufsize = 8096
	tktools.set_transient(self.root, old_context.browser.master)
	history = old_context.app.global_history
	if not history.inhistory_p(url):
	    history.remember_url(url)
	self.root.update_idletasks()

    def create_widgets(self, url, filename, content_length):
	"""Create the widgets in the Toplevel instance."""
	fr, topfr, botfr = tktools.make_double_frame(self.root)
	Label(topfr, text="Downloading %s" % os.path.basename(filename)
	      ).pack(anchor=W, pady='1m')
	Frame(topfr, borderwidth=1, height=2, relief=SUNKEN
	      ).pack(fill=X, pady='1m')
	self.make_labeled_field(topfr, "Source:", url)['width'] = 45
	self.make_labeled_field(topfr, "Destination:", filename)
	Button(botfr, command=self.stop, text="Stop").pack()
	if content_length:
	    self.make_progress_bar(content_length, topfr)
	frame = Frame(topfr)
	frame.pack(fill=X)
	self.__bytes = self.make_labeled_field(frame, "Bytes:", "0", LEFT)
	if content_length:
	    self.__bytes['width'] = len(`content_length`) + 2
	    self.__percent = self.make_labeled_field(
		frame, "Complete:", self.__bytespat % 0.0, LEFT)
	else:
	    self.__percent = None

    __boldpat = regex.compile("-\([a-z]*bold\)-", regex.casefold)
    __datafont = None
    def make_labeled_field(self, master, labeltext, valuetext='', side=TOP):
	frame = Frame(master)
	frame.pack(pady='1m', side=side, anchor=W)
	label = Label(frame, anchor=E, text=labeltext, width=10)
	label.pack(side=LEFT)
	value = Label(frame, anchor=W, text=valuetext)
	if self.__datafont is None:
	    # try to get a medium-weight version of the font if bold:
	    font = label['font']
	    pos = self.__boldpat.search(font) + 1
	    if pos:
		end = pos + len(self.__boldpat.group(1))
		self.__datafont = "%smedium%s" % (font[:pos], font[end:])
	if self.__datafont:
	    try: value['font'] = self.__datafont
	    except TclError: self.__datafont = ''
	value.pack(side=RIGHT, fill=X, expand=1)
	return value

    def message(self, string):
	pass

    __progbar = None
    __bytespat = "%.1f%%"
    def make_progress_bar(self, size, frame):
	self.__bytespat = "%.1f%% of " + grailutil.nicebytes(size)
	self.__maxsize = 1.0 * size	# make it a float for future calc.
	f = Frame(frame, relief=SUNKEN, borderwidth=1, background=LIGHT_BLUE,
		  height=20, width=202)
	f.pack(pady='1m')

	self.__progbar = Frame(f, width=1, background=DARK_BLUE,
			       height=string.atoi(f.cget('height'))
			       - 2*string.atoi(f.cget('borderwidth')))
	self.__progbar.place(x=0, y=0)

    def stop(self):
	self.close()
	if os.path.isfile(self.__filename):
	    try: os.unlink(self.__filename)
	    except IOError, msg: self.context.error_dialog(IOError, msg)

    # file-like methods; these allow us to intercept the close() method
    # on the reader's save file object

    __datasize = 0
    __prevtime = 0.0
    def write(self, data):
	self.__save_file.write(data)
	datasize = self.__datasize = self.__datasize + len(data)
	self.__bytes['text'] = datasize
	if self.__progbar:
	    self.__progbar.config(
		width=max(1, int(datasize * (200 / self.__maxsize))))
	    self.__percent['text'] = (
		self.__bytespat % (100.0 * (datasize / self.__maxsize)))
	    t = time.time()
	    if t - self.__prevtime >= TRANSFER_STATUS_UPDATE_PERIOD:
		self.root.update_idletasks()
		self.__prevtime = t

    def close(self):
	# make sure the 100% mark is updated on the display:
	self.root.update_idletasks()
	self.__reader.stop()
	self.__save_file.close()
	self.__reader.save_file = self.__save_file
	self.__save_file = self.__reader = None
	self.root.destroy()
