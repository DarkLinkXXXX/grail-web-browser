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
import History


# URLs of various sorts
GRAIL_HOME = "http://monty.cnri.reston.va.us/grail/"
PYTHON_HOME = "http://www.python.org/"
ABOUT_GRAIL = "http://monty.cnri.reston.va.us/grail/about/"
DEFAULT_HOME = GRAIL_HOME
LOGO_IMAGES = "http://monty.cnri.reston.va.us/grail/demo/images/at_work/"


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
	self.history = History.History(app)
	self.create_widgets(height)
	self.history_dialog = None

    def create_widgets(self, height):
	self.root = Toplevel(self.master)
	self.root.protocol("WM_DELETE_WINDOW", self.on_delete)
	self.topframe = Frame(self.root)
	self.topframe.pack(fill=X)
	self.create_logo()
	self.create_menubar()
	self.create_urlbar()
	self.create_statusbar()
	self.viewer = Viewer(self.root, self, DefaultStylesheet, height)
	self.animate_logo()

    def create_logo(self):
	self.logo = Frame(self.topframe, relief=RAISED, borderwidth=2)
	self.logo.pack(side=LEFT, padx=5, pady=5)

    def animate_logo(self):
	import ImageLoopItem
	self.logo.grail_browser = self
	saved_readers = self.readers[:]
	self.logo_loop = ImageLoopItem.ImageLoopItem(
	    self.logo, img=LOGO_IMAGES, text="Grail")
	self.readers[:] = saved_readers

    def create_menubar(self):
	# Create menu bar, menus, and menu entries
	# Also create the Stop button (which lives in the menu)

	# Create menu bar
	self.mbar = Frame(self.topframe,
			  relief=RAISED,
			  borderwidth=2)
	self.mbar.pack(fill=X)

	# Create File menu
	self.filebutton = Menubutton(self.mbar, text="File")
	self.filebutton.pack(side=LEFT)

	self.filemenu = Menu(self.filebutton)
	self.filebutton['menu'] = self.filemenu

	self.filemenu.add_command(label="New Window",
			  command=self.new_command,
			  underline=0, accelerator="Alt-N")
	self.root.bind("<Alt-n>", self.new_command)
	self.root.bind("<Alt-N>", self.new_command)
	self.filemenu.add_command(label="Clone Current Window",
			  command=self.clone_command,
			  underline=0, accelerator="Alt-K")
	self.root.bind("<Alt-k>", self.clone_command)
	self.root.bind("<Alt-K>", self.clone_command)
	self.filemenu.add_command(label="View source",
			  command=self.view_source_command,
			  underline=0, accelerator="Alt-V")
	self.root.bind("<Alt-v>", self.view_source_command)
	self.root.bind("<Alt-V>", self.view_source_command)
	self.filemenu.add_command(label='Open Location...',
				  command=self.open_uri_command,
				  underline=5, accelerator='Alt-L')
	self.root.bind('<Alt-l>', self.open_uri_command)
	self.root.bind('<Alt-L>', self.open_uri_command)
	self.filemenu.add_command(label='Open file...',
				  underline=0, accelerator='Alt O',
				  command=self.open_file_command)
	self.root.bind('<Alt-o>', self.open_file_command)
	self.root.bind('<Alt-O>', self.open_file_command)
	self.filemenu.add_separator()
	self.filemenu.add_command(label="Save As...",
			  command=self.save_as_command,
			  underline=0, accelerator="Alt-S")
	self.root.bind("<Alt-s>", self.save_as_command)
	self.root.bind("<Alt-S>", self.save_as_command)
	self.filemenu.add_command(label="Print...",
			  command=self.print_command,
			  underline=0, accelerator="Alt-P")
	self.root.bind("<Alt-p>", self.print_command)
	self.root.bind("<Alt-P>", self.print_command)
	self.filemenu.add_separator()
	self.filemenu.add_command(label="Close",
			  command=self.close_command,
			  underline=0, accelerator="Alt-W")
	self.root.bind("<Alt-w>", self.close_command) # Macintosh origins...
	self.root.bind("<Alt-W>", self.close_command) # Macintosh origins...
	self.filemenu.add_command(label="Quit",
			  command=self.quit_command,
			  underline=0, accelerator="Alt-Q")
	self.root.bind("<Alt-q>", self.quit_command)
	self.root.bind("<Alt-Q>", self.quit_command)

	self.histbutton = Menubutton(self.mbar, text="Go")
	self.histbutton.pack(side=LEFT)

	self.histmenu = Menu(self.histbutton)
	self.histbutton['menu'] = self.histmenu

	self.histmenu.add_command(label="Back",
			  command=self.back_command,
			  underline=0, accelerator="Alt-Left")
	self.root.bind("<Alt-Left>", self.back_command)
	self.histmenu.add_command(label="Reload",
			  command=self.reload_command,
			  underline=0, accelerator="Alt-R")
	self.root.bind("<Alt-r>", self.reload_command)
	self.histmenu.add_command(label="Forward",
			  command=self.forward_command,
			  underline=0, accelerator="Alt-Right")
	self.root.bind("<Alt-Right>", self.forward_command)
	self.histmenu.add_separator()
	self.histmenu.add_command(label='History...',
				  command=self.show_history_command,
				  underline=0, accelerator="Alt-H")
	self.root.bind("<Alt-h>", self.show_history_command)
	self.root.bind("<Alt-H>", self.show_history_command)
	self.histmenu.add_command(label="Home",
			  command=self.home_command)

	# Create the Search menu

	self.searchbutton = Menubutton(self.mbar, text="Search")
	self.searchbutton.pack(side=LEFT)

	self.searchmenu = Menu(self.searchbutton)
	self.searchbutton['menu'] = self.searchmenu
	self.searchmenu.grail_browser = self # Applet compatibility
	import SearchMenu
	SearchMenu.SearchMenu(self.searchmenu)

	# Create the Bookmarks menu

	self.bookmarksbutton = Menubutton(self.mbar, text="Bookmarks")
	self.bookmarksbutton.pack(side=LEFT)

	self.bookmarksmenu = Menu(self.bookmarksbutton)
	self.bookmarksbutton['menu'] = self.bookmarksmenu
	self.bookmarksmenu.grail_browser = self # Applet compatibility
	import Bookmarks
	Bookmarks.BookmarksMenu(self.bookmarksmenu)

	# Create Stop button

	self.stopbutton = Button(self.mbar, text="Stop",
				 state=DISABLED,
				 foreground='#770000', # Darkish red
				 activeforeground='red',
				 padx=0,
				 pady=0,
				 command=self.stop_command)
	self.stopbutton.pack(side=LEFT)
	self.root.bind("<Alt-period>", self.stop_command)

	# List of user menus (reset on page load)
	self.user_menus = []

	# Create Help menu (on far right)
	self.helpbutton = Menubutton(self.mbar, text="Help")
	self.helpbutton.pack(side=RIGHT)

	self.helpmenu = Menu(self.helpbutton)
	self.helpbutton['menu'] = self.helpmenu

	self.helpmenu.add_command(label="About Grail",
			  command=self.about_command)
	self.helpmenu.add_separator()
	self.helpmenu.add_command(label="Grail Home Page",
			  command=self.grail_home_command)
	self.helpmenu.add_command(label="Python Home Page",
			  command=self.python_home_command)

    def create_urlbar(self):
	self.entry, self.entryframe = \
		    tktools.make_form_entry(self.topframe, "URL:")
	self.entry.bind('<Return>', self.load_from_entry)

    def create_statusbar(self):
	self.msg_frame = Frame(self.topframe, height=20)
	self.msg_frame.pack(fill=X, side=BOTTOM)
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
	self.load(string.strip(self.entry.get()))

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
	self.stop()
	scheme, netloc = urlparse.urlparse(url)[:2]
	if not scheme:
	    if not netloc:
		if os.path.exists(url):
		    url = "file:" + url
		else:
		    url = "http://" + url
	    else:
		url = "http:" + url
	self.message("Loading %s" % url, CURSOR_WAIT)
	try:
	    Reader(self, url, method, params,
		   new, show_source, reload)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()

    def post(self, url, data, ctype):
	# Post form data
	url = urlparse.urljoin(self.url, url)
	method = 'POST'
	params = {"Content-length": `len(data)`,
		  "Content-type": ctype,
		  }
	self.stop()
	self.message("Posting to %s" % url, CURSOR_WAIT)
	try:
	    Reader(self, url, method, params, 1, 0, 1, data=data)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()

    def addreader(self, reader):
	self.readers.append(reader)
	self.allowstop()

    def rmreader(self, reader):
	if reader in self.readers:
	    self.readers.remove(reader)
	if not self.readers:
	    self.clearstop()
	    self.message("Done.")
	    self.viewer.remove_temp_tag()

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

    def stop(self):
	for reader in self.readers[:]:
	    reader.kill()

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
	    self.history.append_link(self.url, self.title)
	else:
	    self.history.set_title(self.url, self.title)

    def get_image(self, src):
	image = self.get_async_image(src)
	if image:
	    if not image.load_synchronously(self):
		image = None
	return image

    def get_async_image(self, src):
	if not self.app: return None
	if not src: return None
	url = urlparse.urljoin(self.url, src)
	if not url: return None
	image = self.app.get_cached_image(url)
	if image:
	    if self.app.load_images and not image.loaded:
		image.start_loading(self)
	    return image
	from AsyncImage import AsyncImage
	try:
	    image = AsyncImage(self, url)
	except IOError, msg:
	    image = None
	if image:
	    self.app.set_cached_image(url, image)
	    if self.app.load_images:
		image.start_loading(self)
	return image

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
	self.stop()
	self.root.destroy()
	if self.app: self.app.maybe_quit()

    # Stop command

    def stop_command(self, event=None):
	self.stop()
	self.message("Stopped.")

    # File menu commands

    def new_command(self, event=None):
	b = Browser(self.master, self.app)
	return b

    def clone_command(self, event=None):
	b = Browser(self.master, self.app)
	if self.url:
	    b.load(self.url)
	return b

    def open_uri_command(self, event=None):
	if self.busycheck(): return
	import OpenURIDialog
	dialog = OpenURIDialog.OpenURIDialog(self.master)
	uri = dialog.go()
	if uri: self.load(uri)

    def open_file_command(self, event=None):
	if self.busycheck(): return
	import FileDialog
	dialog = FileDialog.LoadFileDialog(self.master)
	filename = dialog.go()
	if filename: self.load('file:' + filename)

    def view_source_command(self, event=None):
	# File/View Source
	if self.busycheck(): return
	b = Browser(self.master, self.app, height=24)
	b.load(self.url, show_source=1)

    def save_as_command(self, event=None):
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

    def print_command(self, event=None):
	# File/Print...
	if self.busycheck(): return
	import PrintDialog
	PrintDialog.PrintDialog(self, self.url, self.title)

    def close_command(self, event=None):
	# File/Close
	self.close()

    def quit_command(self, event=None):
	# File/Quit
	if self.app: self.app.quit()
	else: self.close()

    # History menu commands

    def home_command(self, event=None):
	home = self.app and self.app.home or DEFAULT_HOME
	self.load(home)

    def back_command(self, event=None):
	uri = self.history.back()
	if not uri: self.root.bell()
	else: self.load(uri, new=0)

    def reload_command(self, event=None):
	if not 0 <= self.current < len(self.history.links()):
	    self.root.bell()
	    return
	self.load(self.history.link(self.current), new=0, reload=1)

    def forward_command(self, event=None):
	uri = self.history.forward()
	if not uri: self.root.bell()
	else: self.load(uri, new=0)

    def show_history_command(self, event=None):
	if not self.history_dialog:
	    self.history_dialog = History.HistoryDialog(self, self.history)
	self.history_dialog.show()

    # Help menu commands

    def about_command(self, event=None):
	self.load(ABOUT_GRAIL)

    def grail_home_command(self, event=None):
	self.load(GRAIL_HOME)

    def python_home_command(self, event=None):
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
