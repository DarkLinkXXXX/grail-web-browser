"""Browser class for web browser."""


# XXX To do:
# - Stop command
# - Options menu to toggle image loading
# - Reload command
# - Etc.


import string
import urllib
import urlparse
from Tkinter import *
import tktools
import os
import sys
from Viewer import Viewer
from AppletHTMLParser import AppletHTMLParser
from DefaultStylesheet import DefaultStylesheet
import ProtocolAPI
import regsub


# URLs of various sorts
GRAIL_HOME = "http://monty.cnri.reston.va.us/grail/"
PYTHON_HOME = "http://www.python.org/"
ABOUT_GRAIL = "http://monty.cnri.reston.va.us/grail/about/"
DEFAULT_HOME = GRAIL_HOME


# Window title prefix
TITLE_PREFIX = "Grail: "


# Various cursor shapes (argument to message())
CURSOR_NORMAL = ''
CURSOR_LINK = 'hand2'
CURSOR_WAIT = 'watch'


# Font used in message area (default is too heavy)
FONT_MESSAGE = "-*-helvetica-medium-r-normal-*-*-100-100-*-*-*-*-*"


class Browser:

    """A browser window provides the user interface to browse the web.

    It is a blatant rip-off of Mosaic's look and feel, with menus,
    buttons, a URL display/entry widget, a feedback area, and (last
    but not least) a viewer widget.

    """

    def __init__(self, master, app=None, height=40):
	self.master = master
	self.app = app
	self.url = ""
	self.history = []
	self.current = -1
	self.reload_applets = 0
	self.create_widgets(height)

    def create_widgets(self, height):
	self.root = Toplevel(self.master)
	self.root.protocol("WM_DELETE_WINDOW", self.on_delete)
	self.menubar = self.create_menubar()
	self.urlbar = self.create_urlbar()
	self.statusbar = self.create_statusbar()
	self.viewer = Viewer(self.root, self, DefaultStylesheet, height)

    def create_menubar(self):
	# Create menu bar, menus, and menu entries

	# Create menu bar
	self.mbar = Frame(self.root,
			  relief=RAISED,
			  borderwidth=2)
	self.mbar.pack(fill=X)

	# Create File menu
	self.filebutton = Menubutton(self.mbar, text='File')
	self.filebutton.pack(side=LEFT)

	self.filemenu = Menu(self.filebutton)
	self.filebutton['menu'] = self.filemenu

	self.filemenu.add(COMMAND, label='New',
			  command=self.new_command)
	self.filemenu.add(COMMAND, label='View source',
			  command=self.view_source_command)
	self.filemenu.add(SEPARATOR)
	self.filemenu.add(COMMAND, label='Save As...',
			  command=self.save_as_command)
	self.filemenu.add(COMMAND, label='Print...',
			  command=self.print_command)
	self.filemenu.add(SEPARATOR)
	self.filemenu.add(COMMAND, label='Close',
			  command=self.close_command)
	self.filemenu.add(COMMAND, label='Quit',
			  command=self.quit_command)

	self.histbutton = Menubutton(self.mbar, text='Go')
	self.histbutton.pack(side=LEFT)

	self.histmenu = Menu(self.histbutton)
	self.histbutton['menu'] = self.histmenu

	self.histmenu.add(COMMAND, label='Back',
			  command=self.back_command)
	self.histmenu.add(COMMAND, label='Reload',
			  command=self.reload_command)
	self.histmenu.add(COMMAND, label='Forward',
			  command=self.forward_command)
	self.histmenu.add(SEPARATOR)
	self.histmenu.add(COMMAND, label='Home',
			  command=self.home_command)

	# List of user menus (reset on page load)
	self.user_menus = []

	# Create Help menu (on far right)
	self.helpbutton = Menubutton(self.mbar, text='Help')
	self.helpbutton.pack(side=RIGHT)

	self.helpmenu = Menu(self.helpbutton)
	self.helpbutton['menu'] = self.helpmenu

	self.helpmenu.add(COMMAND, label='About Grail',
			  command=self.about_command)
	self.helpmenu.add(SEPARATOR)
	self.helpmenu.add(COMMAND, label='Grail Home Page',
			  command=self.grail_home_command)
	self.helpmenu.add(COMMAND, label='Python Home Page',
			  command=self.python_home_command)

    def create_urlbar(self):
	self.entry, self.topframe = tktools.make_form_entry(self.root, "URL:")
	self.entry.bind('<Return>', self.load_from_entry)

    def create_statusbar(self):
	self.msg_frame = Frame(self.root, height=20)
	self.msg_frame.pack(fill=X)
	self.msg_frame.propagate(OFF)
	self.msg = Label(self.msg_frame, anchor=W, font=FONT_MESSAGE)
	self.msg.pack(fill=X, in_=self.msg_frame)

    def enter(self, url):
	if url[:1] != '#':
	    url = urlparse.urljoin(self.url, url)
	self.message(url, CURSOR_LINK)

    def leave(self):
	self.message_clear()

    def load_from_entry(self, event):
	self.follow(self.entry.get())

    def set_entry(self, url):
	self.entry.delete('0', END)
	self.entry.insert(END, url)

    def follow(self, url):
	if url[:1] == '#':
	    self.viewer.scroll_to(url[1:])
	    return
	url = urlparse.urljoin(self.url, url)
	self.load(url)

    def load(self, url, new=1, show_source=0):
	# Load a new URL into the window
	tuple = urlparse.urlparse(url)
	fragment = tuple[-1]
	tuple = tuple[:-1] + ("",)
	url = urlparse.urlunparse(tuple)
	self.message("Following %s" % url, CURSOR_WAIT)
	params = {}
	if self.reload_applets:
	    params['.reload'] = 1
	try:
	    if self.app:
		api = self.app.open_url(url, 'GET', params)
	    else:
		api = ProtocolAPI.protocol_access(url, 'GET', params)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()
	    return
	self.url = self.title = url
	self.message("Loading %s" % url, CURSOR_WAIT)
	self.root.update_idletasks()
	errcode, errmsg, headers = api.getmeta()
	if errcode != 200:
	    self.error_dialog('Error reply', errmsg)
	if headers.has_key('content-type'):
	    content_type = headers['content-type']
	else:
	    content_type = None
	if not content_type:
	    content_type, content_encoding = self.app.guess_type(url)
	else:
	    content_encoding = None
	if headers.has_key('content-encoding'):
	    content_encoding = headers['content-encoding']
	if content_encoding:
	    # XXX Should fix this
	    self.error_dialog("Warning",
			      "unsupported content-encoding: %s"
			      % content_encoding)

	self.root.title(TITLE_PREFIX + self.title)

	for b in self.user_menus:
	    b.destroy()
	self.user_menus[:] = []

	self.set_entry(self.url)

	self.viewer.clear_reset()

	istext = content_type and content_type[:5] == 'text/'
	if show_source and istext:
	    content_type = 'text/plain'
	if content_type == 'text/html':
	    parserclass = AppletHTMLParser
	elif content_type == 'text/plain':
	    parserclass = TextParser
	else:
	    parserclass = self.find_parser_extension(content_type)
	    if not parserclass and istext:
		parserclass = TextParser

	if parserclass:
	    parser = parserclass(self.viewer)
	else:
	    parser = None

	if parser:
	    BUFSIZE = 512
	    if istext:
		last_was_cr = 0
		while 1:
		    message, ready = api.polldata()
		    self.message(message, CURSOR_WAIT)
		    self.root.update_idletasks()
		    buf = api.getdata(BUFSIZE)
		    if not buf: break
		    if last_was_cr and buf[0] == '\n':
			buf = buf[1:]
		    last_was_cr = buf[-1:] == '\r'
		    if '\r' in buf:
			if '\n' in buf:
			    buf = regsub.gsub('\r\n', '\n', buf)
			if '\r' in buf:
			    buf = regsub.gsub('\r', '\n', buf)
		    parser.feed(buf)
	    else:
		while 1:
		    message, ready = api.polldata()
		    self.message(message, CURSOR_WAIT)
		    self.root.update_idletasks()
		    buf = api.getdata(BUFSIZE)
		    if not buf: break
		    parser.feed(buf)
	    parser.close()
	else:
	    self.viewer.send_flowing_data(
		"Sorry, I'm too stupid to display %s data yet\n" %
		content_type)
	    self.viewer.send_flowing_data(
		"(But it sure would make a nice extension :-)\n")
	    self.viewer.send_flowing_data(
		"You can still use the Save As... command to save it!\n")

	api.close()

	self.viewer.freeze()

	if parser and hasattr(parser, 'title'):
	    self.title = parser.title or self.url
	self.root.title(TITLE_PREFIX + self.title)

	self.message_clear()

	if fragment:
	    self.viewer.scroll_to(fragment)

	self.set_history(new)

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

    def set_history(self, new):
	if new:
	    self.current = self.current + 1
	    self.history[self.current:] = [None]
	self.history[self.current] = (self.url, self.title)

    def get_image(self, src):
	if not self.app: return None
	if not src: return None
	url = urlparse.urljoin(self.url, src)
	if not url: return None
	return self.app.get_image(url)

    def message(self, string = None, cursor = None):
	prev = self.msg['text'], self.viewer.get_cursor()
	if string is not None:
	    self.msg['text'] = string
	if cursor is not None:
	    self.viewer.set_cursor(cursor)
	self.root.update_idletasks()
	return prev

    def message_clear(self):
	self.message("", CURSOR_NORMAL)

    def error_dialog(self, exception, msg):
	if self.app:
	    self.app.error_dialog(exception, msg)
	else:
	    print "ERROR:", msg

    def on_delete(self):
	self.close()

    def close(self):
	self.root.destroy()
	if self.app: self.app.maybe_quit()

    # File menu commands

    def new_command(self):
	# File/New
	return Browser(self.master, self.app)

    def view_source_command(self):
	# File/View Source
	b = Browser(self.master, self.app, height=24)
	b.load(self.url, 1, 1)

    def save_as_command(self):
	# File/Save As...
	import FileDialog
	fd = FileDialog.SaveFileDialog(self.root)
	file = fd.go()
	if not file: return
	api = self.app.open_url(self.url, 'GET', {})
	errcode, errmsg, params = api.getmeta()
	if errcode != 200:
	    self.error_dialog('Error reply', errmsg)
	    api.close()
	    return
	try:
	    ofp = open(file, 'w')
	except IOError, msg:
	    api.close()
	    self.error_dialog(IOError, msg)
	    return
	self.message("Saving...", CURSOR_WAIT)
	BUFSIZE = 8*1024
	while 1:
	    buf = api.getdata(BUFSIZE)
	    if not buf: break
	    ofp.write(buf)
	ofp.close()
	api.close()
	self.message_clear()

    def print_command(self):
	# File/Print...
	self.error_dialog(SystemError,
			      "Sorry, printing is not yet supported")

    def close_command(self):
	# File/Close
	self.close()

    def quit_command(self):
	# File/Quit
	if self.app: self.app.quit()
	else: self.close()

    # History menu commands

    def home_command(self):
	home = self.app and self.app.home or DEFAULT_HOME
	self.load(home)

    def back_command(self):
	if self.current <= 0:
	    self.root.bell()
	    return
	self.current = self.current-1
	self.load(self.history[self.current][0], 0)

    def reload_command(self):
	if self.current >= len(self.history):
	    self.root.bell()
	    return
	save_reload_applets = self.reload_applets
	try:
	    self.reload_applets = 1
	    self.load(self.history[self.current][0], 0)
	finally:
	    self.reload_applets = save_reload_applets

    def forward_command(self):
	if self.current+1 >= len(self.history):
	    self.root.bell()
	    return
	self.current = self.current+1
	self.load(self.history[self.current][0], 0)

    # Help menu commands

    def about_command(self):
	self.load(ABOUT_GRAIL)

    def grail_home_command(self):
	self.load(GRAIL_HOME)

    def python_home_command(self):
	self.load(PYTHON_HOME)

    # End of commmands


from formatter import AS_IS


class TextParser:

    title = ""

    def __init__(self, viewer):
	self.viewer = viewer
	self.viewer.new_font((AS_IS, AS_IS, AS_IS, 1))

    def feed(self, data):
	self.viewer.send_literal_data(data)

    def close(self):
	pass



def getenv(s):
    if os.environ.has_key(s): return os.environ[s]
    return None


def test():
    """Test Browser class."""
    import sys
    url = None
    if sys.argv[1:]: url = sys.argv[1]
    root = Tk()
    b = Browser(root)
    if url: b.load(url)
    root.mainloop()


if __name__ == '__main__':
    test()
