"""Browser class."""


import os
import string
import sys
import grailutil

from Tkinter import *
import tktools

import GrailPrefs
from DefaultStylesheet import DefaultStylesheet
from Viewer import Viewer
from AsyncImage import AsyncImage
from Cursors import *


LOGO_IMAGES = "logo:"
FIRST_LOGO_IMAGE = LOGO_IMAGES + "T1.gif"


# Window title prefix
TITLE_PREFIX = "Grail: "




class Browser:
    """The Browser class provides the top-level GUI.

    It is a blatant rip-off of Mosaic's look and feel, with menus, a
    stop button, a URL display/entry area, and (last but not least) a
    viewer area.  But then, so are all other web browsers. :-)

    """
    def __init__(self, master, app=None,
		 width=None, height=None,
		 geometry=None):
	self.master = master
	if not app:
	    import __main__
	    try: app = __main__.app
	    except NameError: pass
	# In common operation, we should always have an app at this point.
	if app:
	    app.add_browser(self)
	    prefs = app.prefs
	self.app = app

	if not width: width = prefs.GetInt('browser', 'default-width')
	if not height: height = prefs.GetInt('browser', 'default-height')

	self.create_widgets(width=width, height=height, geometry=geometry)
	# icon set up
	iconxbm_file = grailutil.which('icon.xbm')
	self.root.iconname('Grail')
	if iconxbm_file:
	    try: self.root.iconbitmap('@' + iconxbm_file)
	    except TclError: pass

    def create_widgets(self, width, height, geometry):
	# I'd like to be able to set the widget name here, but I'm not
	# sure what the correct thing to do is.  Setting it to `grail'
	# is definitely *not* the right thing to do since this causes
	# all sorts of problems.
	self.root = Toplevel(self.master, class_='Grail')
	self._window_title("Grail: New Browser")
	if geometry:
	    self.root.geometry(geometry)
	self.root.protocol("WM_DELETE_WINDOW", self.on_delete)
	self.topframe = Frame(self.root)
	self.topframe.pack(fill=X)
	self.create_logo()
	self.create_menubar()
	self.create_urlbar()
	self.create_statusbar()
	self.viewer = Viewer(self.root, browser=self,
			     stylesheet=DefaultStylesheet,
			     width=width, height=height)
	self.context = self.viewer.context
	if not grailutil.getenv("GRAIL_NO_LOGO") and sys.platform != 'mac':
	    self.logo_init()

    def create_logo(self):
	self.logo = Button(self.topframe,
			   text="Stop",
			   command=self.stop_command,
			   state=DISABLED)
	self.logo.pack(side=LEFT, fill=BOTH, padx=10, pady=10)
	self.root.bind("<Alt-period>", self.stop_command)
	self.logo_animate = 0

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
	self.filemenu.add_command(label="View Source",
			  command=self.view_source_command,
			  underline=0, accelerator="Alt-V")
	self.root.bind("<Alt-v>", self.view_source_command)
	self.root.bind("<Alt-V>", self.view_source_command)
	self.filemenu.add_command(label='Open Location...',
				  command=self.open_uri_command,
				  underline=5, accelerator='Alt-L')
	self.root.bind('<Alt-l>', self.open_uri_command)
	self.root.bind('<Alt-L>', self.open_uri_command)
	self.filemenu.add_command(label='Open File...',
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
	self.root.bind("<Alt-R>", self.reload_command)
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
	SearchMenu.SearchMenu(self.searchmenu, self.root, self)

	# Create the Bookmarks menu

	self.bookmarksbutton = Menubutton(self.mbar, text="Bookmarks")
	self.bookmarksbutton.pack(side=LEFT)

	self.bookmarksmenu = Menu(self.bookmarksbutton)
	self.bookmarksbutton['menu'] = self.bookmarksmenu
	self.bookmarksmenu.grail_browser = self # Applet compatibility
	import Bookmarks
	Bookmarks.BookmarksMenu(self.bookmarksmenu)

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
	self.helpmenu.add_command(label='The Python Software Activity (PSA)',
				  command=self.psa_home_command)
	self.helpmenu.add_command(label="CNRI Home Page",
			  command=self.cnri_home_command)

    def create_urlbar(self):
	self.entry, self.entryframe = \
		    tktools.make_form_entry(self.topframe, "URL:")
	self.entry.bind('<Return>', self.load_from_entry)

    def create_statusbar(self):
	self.msg_frame = Frame(self.topframe, height=20)
	self.msg_frame.pack(fill=X, side=BOTTOM)
	self.msg_frame.propagate(OFF)
	self.msg = Label(self.msg_frame, anchor=W,
			 font=self.app.prefs.Get('presentation',
						 'message-font'))

	self.msg.pack(fill=X, in_=self.msg_frame)

    # --- External interfaces ---

    def get_async_image(self, src):
	# XXX This is here for the 0.2 ImageLoopItem applet only
	return self.context.get_async_image(src)

    def allowstop(self):
	self.logo_start()

    def clearstop(self):
	self.logo_stop()

    def clear_reset(self):
	for b in self.user_menus:
	    b.destroy()
	self.user_menus[:] = []
	self.set_url("")
	self.viewer.clear_reset()

    def set_url(self, url):
	self.set_entry(url)
	self.set_title(url)

    def set_title(self, title):
	self._window_title(TITLE_PREFIX + title)

    def message(self, string = "", cursor = None):
	msg = self.msg['text']
	self.msg['text'] = string
	if not cursor:
	    if self.context.busy():
		cursor = CURSOR_WAIT
	    else:
		cursor = CURSOR_NORMAL
	self.viewer.set_cursor(cursor)
	if cursor == CURSOR_WAIT:
	    self.root.update_idletasks()

    def message_clear(self):
	self.message("")

    def error_dialog(self, exception, msg):
	if self.app:
	    self.app.error_dialog(exception, msg, root=self.root)
	else:
	    print "ERROR:", msg

    # --- Internals ---

    def _window_title(self, title):
	self.root.title(title)
	self.root.iconname(title)

    def set_entry(self, url):
	self.entry.delete('0', END)
	self.entry.insert(END, url)

    def close(self):
	self.context.stop()
	self.root.destroy()
	if self.app:
	    self.app.del_browser(self)
	    self.app.maybe_quit()

    # --- Callbacks ---

    # WM_DELETE_WINDOW on toplevel

    def on_delete(self):
	self.close()

    # <Return> in URL entry field

    def load_from_entry(self, event):
	url = string.strip(self.entry.get())
	if url:
	    self.context.load(grailutil.complete_url(url))
	else:
	    self.root.bell()

    # Stop command

    def stop_command(self, event=None):
	if self.context.busy():
	    self.context.stop()
	    self.message("Stopped.")

    # File menu commands

    def new_command(self, event=None):
	b = Browser(self.master, self.app)
	return b

    def clone_command(self, event=None):
	b = Browser(self.master, self.app)
	b.context.clone_history_from(self.context)
	return b

    def open_uri_command(self, event=None):
	import OpenURIDialog
	dialog = OpenURIDialog.OpenURIDialog(self.root)
	uri = dialog.go()
	if uri:
	    uri = string.strip(uri)
	    if uri:
		self.context.load(grailutil.complete_url(uri))

    def open_file_command(self, event=None):
	import FileDialog
	dialog = FileDialog.LoadFileDialog(self.master)
	filename = dialog.go()
	if filename:
	    import urllib
	    self.context.load('file:' + urllib.quote(filename))

    def view_source_command(self, event=None):
	# File/View Source
	b = Browser(self.master, self.app, height=24)
	b.context.load(self.context.get_url(), show_source=1)

    def save_as_command(self, event=None):
	# File/Save As...
	if self.context.busycheck(): return
	import FileDialog
	fd = FileDialog.SaveFileDialog(self.root)
	# give it a default filename on which save within the
	# current directory
	urlasfile = string.splitfields(self.context.get_url(), '/')
	default = urlasfile[-1]
	# maybe bogus assumption?
	if not default: default = 'index.html'
	file = fd.go(default=default)
	if not file: return
	api = self.app.open_url(self.context.get_url(), 'GET', {})
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
	if self.context.busycheck(): return
	import PrintDialog
	PrintDialog.PrintDialog(self.context,
				self.context.get_url(),
				self.context.get_title())

    def close_command(self, event=None):
	# File/Close
	self.close()

    def quit_command(self, event=None):
	# File/Quit
	if self.app: self.app.quit()
	else: self.close()

    # History menu commands

    def home_command(self, event=None):
	home = self.app.prefs.Get('landmarks', 'home-page')
	if not home:
	    home = self.app.prefs.Get('landmarks', 'grail-home-page')
	self.context.load(home)

    def reload_command(self, event=None):
	self.context.reload_page()

    def forward_command(self, event=None):
	self.context.go_forward()

    def back_command(self, event=None):
	self.context.go_back()

    def show_history_command(self, event=None):
	self.context.show_history_dialog()

    # Help menu commands

    def about_command(self, event=None):
	self.context.load(self.app.prefs.Get('landmarks', 'about-grail-page'))
    def grail_home_command(self, event=None):
	self.context.load(self.app.prefs.Get('landmarks', 'grail-home-page'))
    def python_home_command(self, event=None):
	self.context.load(self.app.prefs.Get('landmarks', 'python-home-page'))
    def psa_home_command(self, event=None):
	self.context.load(self.app.prefs.Get('landmarks', 'psa-home-page'))
    def cnri_home_command(self, event=None):
	self.context.load(self.app.prefs.Get('landmarks', 'cnri-home-page'))

    # --- Animated logo ---

    def logo_init(self):
	self.logo_index = 0
	self.logo_id = None
	self.logo_more = None
	self.logo_images = []
	self.logo_image = AsyncImage(self.context, FIRST_LOGO_IMAGE)
	self.logo_image.load_synchronously()
	self.logo.config(image=self.logo_image, state=NORMAL)
	self.logo_images = [self.logo_image]
	self.logo_more = self.logo_image.loaded
	self.logo_animate = 1

    def logo_next(self):
	self.logo_id = None
	self.logo_id = self.root.after(200, self.logo_next)
	if self.logo_more:
	    url = LOGO_IMAGES + "T%d.gif" % len(self.logo_images)
	    image = AsyncImage(self.context, url)
	    image.load_synchronously()
	    self.logo_more = image.loaded
	    if self.logo_more:
		self.logo_images.append(image)
	if self.logo_images:
	    self.logo_index = (self.logo_index + 1) % len(self.logo_images)
	    self.logo.config(image=self.logo_images[self.logo_index])

    def logo_start(self):
	self.logo.config(state=NORMAL)
	if not self.logo_animate:
	    return
	if not self.logo_id:
	    self.logo_index = 0
	    self.logo_next()

    def logo_stop(self):
	if not self.logo_animate:
	    self.logo.config(state=DISABLED)
	    return
	if self.logo_id:
	    self.root.after_cancel(self.logo_id)
	    self.logo_id = None
	self.logo.config(image=self.logo_image)

    # --- API for searching ---

    def search_for_pattern(self, pattern,
			   regex_flag, case_flag, backwards_flag):
	textwidget = self.viewer.text
	try:
	    index = textwidget.index(SEL_FIRST)
	    index = '%s + %s chars' % (str(index),
				       backwards_flag and '0' or '1')
	except TclError:
	    index = '1.0'
	length = IntVar()
	hitlength = None
	hit = textwidget.search(pattern, index, count=length,
				nocase=not case_flag,
				regexp=regex_flag,
				backwards=backwards_flag)
	if hit:
	    try:
		textwidget.tag_remove(SEL, SEL_FIRST, SEL_LAST)
	    except TclError:
		pass
	    hitlength = length.get()
	    textwidget.tag_add(SEL, hit, "%s + %s chars" % (hit, hitlength))
	    textwidget.yview_pickplace(SEL_FIRST)
	return hit


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
