# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""Browser class."""


import os
import string
import sys
import grailutil

from Tkinter import *
import tktools

from Viewer import Viewer
from Cursors import *


LOGO_IMAGES = "logo:"
FIRST_LOGO_IMAGE = LOGO_IMAGES + "T1.gif"


# Window title prefix
TITLE_PREFIX = "Grail: "


# If we have an icon file, replace tktools.make_toplevel so that it gets
# set up as the icon, otherwise don't do anything magic.
#
_iconxbm_file = grailutil.which('icon.xbm')
def make_toplevel(*args, **kw):
    w = apply(tktools_make_toplevel, args, kw)
    # icon set up
    try: w.iconbitmap('@' + _iconxbm_file)
    except TclError: pass
    return w

if _iconxbm_file:
    tktools_make_toplevel = tktools.make_toplevel
    tktools.make_toplevel = make_toplevel



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
	    app = grailutil.get_grailapp()
	# In common operation, we should always have an app at this point.
	if app:
	    app.add_browser(self)
	    prefs = app.prefs
	self.app = app

	if not width: width = prefs.GetInt('browser', 'default-width')
	if not height: height = prefs.GetInt('browser', 'default-height')

	self.create_widgets(width=width, height=height, geometry=geometry)
	self.root.iconname('Grail')

    def create_widgets(self, width, height, geometry):
	# I'd like to be able to set the widget name here, but I'm not
	# sure what the correct thing to do is.  Setting it to `grail'
	# is definitely *not* the right thing to do since this causes
	# all sorts of problems.
	self.root = tktools.make_toplevel(self.master, class_='Grail')
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
			     width=width, height=height)
	self.context = self.viewer.context
	if self.app.prefs.GetBoolean('browser', 'show-logo'):
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
				  underline=0, accelerator='Alt-O',
				  command=self.open_file_command)
	self.root.bind('<Alt-o>', self.open_file_command)
	self.root.bind('<Alt-O>', self.open_file_command)
	self.filemenu.add_command(label='Open Selection',
				  underline=6, accelerator='Alt-E',
				  command=self.open_selection_command)
	self.root.bind('<Alt-e>', self.open_selection_command)
	self.root.bind('<Alt-E>', self.open_selection_command)
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
	import DocumentInfo
	cmd = DocumentInfo.DocumentInfoCommand(self)
	self.filemenu.add_command(label="Document Info...", command=cmd,
				  accelerator="Alt-D", underline=0)
	self.root.bind("<Alt-d>", cmd)
	self.root.bind("<Alt-D>", cmd)
	self.filemenu.add_separator()
	self.filemenu.add_command(label="I/O Status Panel...",
				  command=self.iostatus_command,
				  underline=0, accelerator="Alt-I")
	self.root.bind("<Alt-i>", self.iostatus_command)
	self.root.bind("<Alt-I>", self.iostatus_command)
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
	self.bookmarksmenu_menu = Bookmarks.BookmarksMenu(self.bookmarksmenu)

	# Create the Preferences menu

	self.preferencesbutton = Menubutton(self.mbar, text="Preferences")
	self.preferencesbutton.pack(side=LEFT)

	self.preferencesmenu = Menu(self.preferencesbutton)
	self.preferencesbutton['menu'] = self.preferencesmenu
	from PrefsPanels import PrefsPanelsMenu
	PrefsPanelsMenu(self.preferencesmenu, self)

	# List of user menus (reset on page load)
	self.user_menus = []

	# Create Help menu (on far right)
	raw = self.app.prefs.Get('browser', 'help-menu')
	lines = filter(None, map(string.strip, string.split(raw, '\n')))
	if not lines:
	    return

	self.helpbutton = Menubutton(self.mbar, text="Help", name='help')
	self.helpbutton.pack(side=RIGHT)

	self.helpmenu = Menu(self.helpbutton, name='menu')
	self.helpbutton['menu'] = self.helpmenu

	i = 0
	n = len(lines) - 1
	while i < n:
	    label = lines[i]
	    i = i+1
	    if label == '-':
		self.helpmenu.add_separator()
	    else:
		url = lines[i]
		i = i+1
		command = HelpMenuCommand(self, url)
		self.helpmenu.add_command(label=label, command=command)

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

    def set_url(self, url):
	self.set_entry(url)
	self.set_title(url)

    def set_title(self, title):
	self._window_title(TITLE_PREFIX + title)

    def message(self, string = ""):
	self.msg['text'] = string

    def messagevariable(self, variable=None):
	if variable:
	    self.msg['textvariable'] = variable
	else:
	    self.msg['textvariable'] = ""
	    self.msg['text'] = ""
    message_clear = messagevariable

    def error_dialog(self, exception, msg):
	if self.app:
	    self.app.error_dialog(exception, msg, root=self.root)
	else:
	    print "ERROR:", msg

    def load(self, *args, **kw):
	"""Interface for applets."""
	return apply(self.context.load, args, kw)

    def valid(self):
	return self.app and self in self.app.browsers

    # --- Internals ---

    def _window_title(self, title):
	self.root.title(title)
	self.root.iconname(title)

    def set_entry(self, url):
	self.entry.delete('0', END)
	self.entry.insert(END, url)

    def close(self):
	self.context.stop()
	self.viewer.close()
	self.root.destroy()
	self.bookmarksmenu_menu.close()
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
	uri, new = dialog.go()
	if uri:
	    if new:
		browser = Browser(self.master, self.app)
	    else:
		browser = self
	    browser.context.load(grailutil.complete_url(uri))

    def open_file_command(self, event=None):
	import FileDialog
	dialog = FileDialog.LoadFileDialog(self.master)
	filename = dialog.go(key="load")
	if filename:
	    import urllib
	    self.context.load('file:' + urllib.pathname2url(filename))

    def open_selection_command(self, event=None):
	try:
	    selection = self.root.selection_get()
	except TclError:
	    self.root.bell()
	    return
	uri = string.joinfields(string.split(selection), '')
	self.context.load(grailutil.complete_url(uri))

    def view_source_command(self, event=None):
	self.context.view_source()

    def save_as_command(self, event=None):
	self.context.save_document()

    def print_command(self, event=None):
	self.context.print_document()

    def iostatus_command(self, event=None):
	self.app.open_io_status_panel()

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
	    home = self.app.prefs.Get('landmarks', 'default-home-page')
	self.context.load(home)

    def reload_command(self, event=None):
	self.context.reload_page()

    def forward_command(self, event=None):
	self.context.go_forward()

    def back_command(self, event=None):
	self.context.go_back()

    def show_history_command(self, event=None):
	self.context.show_history_dialog()

    # --- Animated logo ---

    def logo_init(self):
	"""Initialize animated logo and display the first image.

	This doesn't start the animation sequence -- use logo_start()
	for that.

	"""
	self.logo_index = 0		# Currently displayed image
	self.logo_last = -1		# Last image; -1 if unknown
	self.logo_id = None		# Tk id of timer callback
	self.logo_animate = 1		# True if animating
	self.logo_next()

    def logo_next(self):
	"""Display the next image in the logo animation sequence.

	If the first image can't be found, disable animation.

	"""
	self.logo_index = self.logo_index + 1
	if self.logo_last > 0 and self.logo_index > self.logo_last:
	    self.logo_index = 1
	entytyname = "grail.logo.%d" % self.logo_index
	image = self.app.load_dingbat(entytyname)
	if not image:
	    if self.logo_index == 1:
		self.logo_animate = 0
		return
	    self.logo_index = 1
	    entytyname = "grail.logo.%d" % self.logo_index
	    image = self.app.load_dingbat(entytyname)
	    if not image:
		self.logo_animate = 0
		return
	self.logo.config(image=image, state=NORMAL)

    def logo_start(self):
	"""Start logo animation.

	If we can't/don't animate the logo, enable the stop button instead.

	"""
	self.logo.config(state=NORMAL)
	if not self.logo_animate:
	    return
	if not self.logo_id:
	    self.logo_index = 0
	    self.logo_next()
	    self.logo_id = self.root.after(200, self.logo_update)

    def logo_stop(self):
	"""Stop logo animation.

	If we can't/don't animate the logo, disable the stop button instead.

	"""
	if not self.logo_animate:
	    self.logo.config(state=DISABLED)
	    return
	if self.logo_id:
	    self.root.after_cancel(self.logo_id)
	    self.logo_id = None
	self.logo_index = 0
	self.logo_next()

    def logo_update(self):
	"""Keep logo animation going."""
	self.logo_id = None
	if self.logo_animate:
	    self.logo_next()
	    if self.logo_animate:
		self.logo_id = self.root.after(200, self.logo_update)

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


class HelpMenuCommand:
    """Encapsulate a menu item into a callable object to load the resource.
    """
    def __init__(self, browser, url):
	self.__browser = browser
	self.__url = url

    def __call__(self, event=None):
	self.__browser.context.load(self.__url)


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
