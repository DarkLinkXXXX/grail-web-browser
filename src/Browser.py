"""Browser class for web browser."""


import os
import regsub
import string
import sys
import urlparse

from Tkinter import *
import tktools

from DefaultStylesheet import DefaultStylesheet
from Reader import Reader
from Viewer import Viewer


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
	self.readers = []
	self.url = ""
	self.title = ""
	self.history = []
	self.current = -1
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
	# Also create the Stop button (which lives in the menu)

	# Create menu bar
	self.mbar = Frame(self.root,
			  relief=RAISED,
			  borderwidth=2)
	self.mbar.pack(fill=X)

	# Create File menu
	self.filebutton = Menubutton(self.mbar, text="File")
	self.filebutton.pack(side=LEFT)

	self.filemenu = Menu(self.filebutton)
	self.filebutton['menu'] = self.filemenu

	self.filemenu.add(COMMAND, label="New",
			  command=self.new_command)
	self.filemenu.add(COMMAND, label="View source",
			  command=self.view_source_command)
	self.filemenu.add(SEPARATOR)
	self.filemenu.add(COMMAND, label="Save As...",
			  command=self.save_as_command)
	self.filemenu.add(COMMAND, label="Print...",
			  command=self.print_command)
	self.filemenu.add(SEPARATOR)
	self.filemenu.add(COMMAND, label="Close",
			  command=self.close_command)
	self.filemenu.add(COMMAND, label="Quit",
			  command=self.quit_command)

	self.histbutton = Menubutton(self.mbar, text="Go")
	self.histbutton.pack(side=LEFT)

	self.histmenu = Menu(self.histbutton)
	self.histbutton['menu'] = self.histmenu

	self.histmenu.add(COMMAND, label="Back",
			  command=self.back_command)
	self.histmenu.add(COMMAND, label="Reload",
			  command=self.reload_command)
	self.histmenu.add(COMMAND, label="Forward",
			  command=self.forward_command)
	self.histmenu.add(SEPARATOR)
	self.histmenu.add(COMMAND, label="Home",
			  command=self.home_command)

	# Create Stop button

	self.stopbutton = Button(self.mbar, text="Stop",
				 state=DISABLED,
				 foreground='#770000', # Darkish red
				 activeforeground='red',
				 padx=0,
				 pady=0,
				 command=self.stop_command)
	self.stopbutton.pack(side=LEFT)

	# List of user menus (reset on page load)
	self.user_menus = []

	# Create Help menu (on far right)
	self.helpbutton = Menubutton(self.mbar, text="Help")
	self.helpbutton.pack(side=RIGHT)

	self.helpmenu = Menu(self.helpbutton)
	self.helpbutton['menu'] = self.helpmenu

	self.helpmenu.add(COMMAND, label="About Grail",
			  command=self.about_command)
	self.helpmenu.add(SEPARATOR)
	self.helpmenu.add(COMMAND, label="Grail Home Page",
			  command=self.grail_home_command)
	self.helpmenu.add(COMMAND, label="Python Home Page",
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
	if self.busy(): return
	if url[:1] != '#':
	    url = urlparse.urljoin(self.url, url)
	self.message(url, CURSOR_LINK)

    def leave(self):
	if self.busy(): return
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

    def load(self, url, method='GET', params={},
	     new=1, show_source=0, reload=0):
	# Start loading a new URL into the window
	self.stop("Stopped.")
	self.message("Loading %s" % url)
	try:
	    reader = Reader(self, url, method, params,
			    new, show_source, reload)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()
	else:
	    self.readers.append(reader)

    def rmreader(self, reader):
	if reader in self.readers:
	    self.readers.remove(reader)

    def busy(self):
	return not not self.readers

    def busycheck(self):
	if self.readers:
	    self.error_dialog('Busy',
		"Please wait until the transfer is done (or stop it)")
	    return 1
	return 0

    def allowstop(self):
	self.stopbutton['state'] = NORMAL

    def clearstop(self):
	self.stopbutton['state'] = DISABLED

    def stop(self, msg):
	for reader in self.readers[:]:
	    reader.stop(msg)

    def clear_reset(self, url, new):
	for b in self.user_menus:
	    b.destroy()
	self.url = url
	self.title = self.url
	self.user_menus[:] = []
	self.set_entry(self.url)
	self.root.title(TITLE_PREFIX + self.title)
	self.viewer.clear_reset()
	self.set_history(new)

    def set_title(self, title):
	self.title = title
	self.root.title(TITLE_PREFIX + self.title)
	self.set_history(0)

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

    def get_cached_image(self, src):
	if not self.app: return None
	if not src: return None
	url = urlparse.urljoin(self.url, src)
	if not url: return None
	return self.app.get_cached_image(url)

    def message(self, string = "", cursor = None):
	msg = self.msg['text']
	crs = None			# B/W compat hack
	self.msg['text'] = string
	if not cursor:
	    if self.readers:
		cursor = CURSOR_WAIT
	    else:
		cursor = CURSOR_NORMAL
	self.viewer.set_cursor(cursor)
	self.root.update_idletasks()
	return msg, crs

    def message_clear(self):
	self.message("")

    def error_dialog(self, exception, msg):
	if self.app:
	    self.app.error_dialog(exception, msg)
	else:
	    print "ERROR:", msg

    def on_delete(self):
	self.close()

    def close(self):
	self.stop("Closed.")
	self.root.destroy()
	if self.app: self.app.maybe_quit()

    # Stop command

    def stop_command(self):
	self.stop("Stopped.")

    # File menu commands

    def new_command(self):
	# File/New
	return Browser(self.master, self.app)

    def view_source_command(self):
	# File/View Source
	if self.busycheck(): return
	b = Browser(self.master, self.app, height=24)
	b.load(self.url, show_source=1, new=1)

    def save_as_command(self):
	# File/Save As...
	if self.busycheck(): return
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
	if self.busycheck(): return
	import PrintDialog
	PrintDialog.PrintDialog(self, self.url, self.title)

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
	self.load(self.history[self.current][0], new=0)

    def reload_command(self):
	if self.current >= len(self.history):
	    self.root.bell()
	    return
	self.load(self.history[self.current][0], new=0, reload=1)

    def forward_command(self):
	if self.current+1 >= len(self.history):
	    self.root.bell()
	    return
	self.current = self.current+1
	self.load(self.history[self.current][0], new=0)

    # Help menu commands

    def about_command(self):
	self.load(ABOUT_GRAIL)

    def grail_home_command(self):
	self.load(GRAIL_HOME)

    def python_home_command(self):
	self.load(PYTHON_HOME)

    # End of commmands


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
