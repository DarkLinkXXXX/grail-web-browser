"""Browser class for web browser."""


# XXX To do:
# - Stop command
# - Options menu to toggle image loading
# - Reload command
# - Etc.


import urllib
import urlparse
from Tkinter import *
import tktools
from Viewer import Viewer
from AppletHTMLParser import AppletHTMLParser
from DefaultStylesheet import DefaultStylesheet


# URLs of various sorts
DEFAULT_HOME = 'http://monty.cnri.reston.va.us/grail/'
ABOUT_GRAIL = 'http://monty.cnri.reston.va.us/grail/about/'


# Various cursor shapes (argument to message())
CURSOR_NORMAL = ''
CURSOR_LINK = 'hand2'
CURSOR_WAIT = 'watch'


# Font used in message area (default is too heavy)
FONT_MESSAGE = '-*-helvetica-medium-r-normal-*-*-100-100-*-*-*-*-*'


class Browser:

    """A browser window provides the user interface to browse the web.

    It is a blatant rip-off of Mosaic's look and feel, with menus,
    buttons, a URL display/entry widget, a feedback area, and (last
    but not least) a viewer widget.

    """

    def __init__(self, master, app=None):
	self.master = master
	self.app = app
	self.url = ''
	self.history = []
	self.current = -1
	self.create_widgets()

    def create_widgets(self):
	self.root = Toplevel(self.master)
	self.root.protocol("WM_DELETE_WINDOW", self.on_delete)
	self.menubar = self.create_menubar()
	self.urlbar = self.create_urlbar()
	self.statusbar = self.create_statusbar()
	self.viewer = Viewer(self.root, self, DefaultStylesheet)

    def create_menubar(self):
	# Create menu bar, menus, and menu entries

	# Create menu bar
	self.mbar = Frame(self.root,
			  relief='raised',
			  borderwidth=2)
	self.mbar.pack(fill='x')

	# Create File menu
	self.filebutton = Menubutton(self.mbar, text='File')
	self.filebutton.pack(side='left')

	self.filemenu = Menu(self.filebutton)
	self.filebutton['menu'] = self.filemenu

	self.filemenu.add('command', label='New',
			  command=self.new_command)
	self.filemenu.add('separator')
	self.filemenu.add('command', label='Close',
			  command=self.close_command)
	self.filemenu.add('command', label='Quit',
			  command=self.quit_command)

	self.histbutton = Menubutton(self.mbar, text='Go')
	self.histbutton.pack(side='left')

	self.histmenu = Menu(self.histbutton)
	self.histbutton['menu'] = self.histmenu

	self.histmenu.add('command', label='Back',
			  command=self.back_command)
	self.histmenu.add('command', label='Forward',
			  command=self.forward_command)
	self.histmenu.add('separator')
	self.histmenu.add('command', label='Home',
			  command=self.home_command)

	# List of user menus (reset on page load)
	self.user_menus = []

	# Create Help menu (on far right)
	self.helpbutton = Menubutton(self.mbar, text='Help')
	self.helpbutton.pack(side='right')

	self.helpmenu = Menu(self.helpbutton)
	self.helpbutton['menu'] = self.helpmenu

	self.helpmenu.add('command', label='About Grail...',
			  command=self.about_command)

    def create_urlbar(self):
	self.entry, self.topframe = tktools.make_form_entry(self.root, 'URL:')
	self.entry.bind('<Return>', self.load_from_entry)

    def create_statusbar(self):
	self.msg = Label(self.root, anchor='w', font=FONT_MESSAGE)
	self.msg.pack(fill='x')

    def enter(self, url):
	if url[:1] != '#':
	    url = urlparse.urljoin(self.url, url)
	self.message(url, CURSOR_LINK)

    def leave(self):
	self.message()

    def load_from_entry(self, event):
	self.follow(self.entry.get())

    def set_entry(self, url):
	self.entry.delete('0', 'end')
	self.entry.insert('end', url)

    def follow(self, url):
	if url[:1] == '#':
	    self.viewer.scroll_to(url[1:])
	    return
	url = urlparse.urljoin(self.url, url)
	self.load(url)

    def load(self, url, new=1):
	# Load a new URL into the window
	tuple = urlparse.urlparse(url)
	fragment = tuple[-1]
	tuple = tuple[:-1] + ('',)
	url = urlparse.urlunparse(tuple)
	self.message('Following %s' % url, CURSOR_WAIT)
	if self.app:
	    fp, url, content_type = self.app.open_url(url)
	else:
	    # Fallback for test() only
	    fp = urllib.urlopen(url)
	    if url[-5:] == '.html':
		content_type = 'text/html'
	    else:
		content_type = 'text/plain'
	if not fp:
	    self.message()
	    return

	self.url = url
	self.message('Loading %s' % url, CURSOR_WAIT)

	self.root.title('Grail Browser: ' + self.url)

	for b in self.user_menus:
	    b.destroy()
	self.user_menus[:] = []

	self.set_entry(self.url)

	self.viewer.clear_reset()

	if content_type == 'text/html':
	    parser = AppletHTMLParser(self.viewer)
	elif content_type and content_type[:5] == 'text/':
	    parser = TextParser(self.viewer)
	else:
	    parser = None

	if parser:
	    while 1:
		line = fp.readline()
		if not line: break
		parser.feed(line)
		self.root.update_idletasks()
	    parser.close()
	else:
	    print "Should save it..."

	fp.close()

	self.title = parser.title or self.url
	self.root.title('Grail Browser: ' + self.title)

	self.message()

	if fragment:
	    self.viewer.scroll_to(fragment)

	self.set_history(new)

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

    def message(self, string = '', cursor = CURSOR_NORMAL):
	prev = self.msg['text'], self.viewer.get_cursor()
	self.msg['text'] = string
	self.viewer.set_cursor(cursor)
	self.root.update_idletasks()
	return prev

    def on_delete(self):
	self.close()

    def close(self):
	self.root.destroy()
	if self.app: self.app.maybe_quit()

    # File menu commands

    def new_command(self):
	# File/New...
	return Browser(self.master, self.app)

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

    def forward_command(self):
	if self.current+1 >= len(self.history):
	    self.root.bell()
	    return
	self.current = self.current+1
	self.load(self.history[self.current][0], 0)

    # Help menu commands

    def about_command(self):
	self.load(ABOUT_GRAIL)

    # End of commmands


class TextParser:

    title = ''

    def __init__(self, viewer):
	self.viewer = viewer

    def feed(self, data):
	self.viewer.add_data(data, 'tt')

    def close(self):
	pass


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
