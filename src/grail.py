#! /home/guido/depot/bin/python


"""Grail -- an extensible web browser.

This leverages of Tkinter, urllib/urlparse, sgmllib/htmllib, rexec...

"""


__version__ = "0.2b1"			# I.e. PRE 0.2


import sys
import getopt
import string
import urllib
urllib._urlopener = urllib.URLopener()	# Don't want it too clever
import tempfile
import posixpath
import os
import traceback
from Tkinter import *
import SafeDialog
import tktools
from Browser import Browser, DEFAULT_HOME
import SafeTkinter
from AppletRExec import AppletRExec
if 0:
    import dummies

# Milliseconds between interrupt checks
KEEPALIVE_TIMER = 1000


def main():
    try:
	opts, args = getopt.getopt(sys.argv[1:], 'g:i')
    except getopt.error, msg:
	print msg
	sys.exit(2)
    geometry = None
    load_images = 1
    for o, a in opts:
	if o == '-i':
	    load_images = 0
	if o == '-g':
	    geometry = a
    if args:
	if args[1:]:
	    print "Usage: %s [-g geometry] [-i] [url]" % sys.argv[0]
	    sys.exit(2)
	url = args[0]
    else:
	url = None
    app = Application()
    app.load_images = load_images
    browser = Browser(app.root, app)
    if geometry:
	browser.root.geometry(geometry)
	self.root.update_idletasks()	# Get geometry implemented
    if url:
	app.home = url
    browser.load(app.home)
    SafeTkinter._castrate(app.root.tk)
    app.go()


class MyURLopener(urllib.URLopener):

    openers = {}
    
    def open_unknown(self, fullurl):
	type, url = urllib.splittype(fullurl)
	if self.openers.has_key(type):
	    opener = self.openers[type]
	else:
	    opener = self.openers[type] = self.find_extension(type)
	if opener:
	    return opener(url)
	print "Unknown URL type:", type
	return urllib.URLopener.open_unknown(self, fullurl)

    def find_extension(self, type):
	home = getenv("HOME") or os.curdir
	graildir = getenv("GRAILDIR") or os.path.join(home, ".grail")
	protodir = os.path.join(graildir, "protocols")
	if protodir not in sys.path: sys.path.insert(0, protodir)
	cmd = "import %s; opener = %s.open_%s" % (type, type, type)
	try:
	    exec cmd
	    return opener
	except ImportError:
	    return None
	except:
	    print "-"*40
	    print "Exception occurred during import of %s:" % type
	    traceback.print_exc()
	    print "-"*40
	    return None

def getenv(s):
    if os.environ.has_key(s): return os.environ[s]
    return None


class Application:

    """The application class represents a group of browser windows."""

    def __init__(self):
	self.load_images = 1
	self.home = DEFAULT_HOME
	self.image_cache = {}
	self.rexec = AppletRExec(None, 2)
	self.urlopener = MyURLopener()
	self.root = Tk()
	self.root.withdraw()
##	self.quit_button = Button(self.root, text='Quit', command=self.quit)
##	self.quit_button.pack()
	self.keep_alive()

    def quit(self):
	self.root.destroy()

    def maybe_quit(self):
	if not self.root.children:
	    self.quit()

    def go(self):
	self.root.mainloop()

    def keep_alive(self):
	# Exercise the Python interpreter regularly so keyboard
	# interrupts get through
	self.root.tk.createtimerhandler(KEEPALIVE_TIMER, self.keep_alive)

    def get_image(self, url, force=0):
	if not url or not self.load_images and not force:
	    return None
	if self.image_cache.has_key(url):
	    return self.image_cache[url]
	fp, url, content_type = self.open_url(url, 0)
	if not fp:
	    return None
	if content_type and content_type[:6] != 'image/':
	    print '***', url, 'is not an image'
	    fp.close()
	    return None
	if content_type[6:] in ('x-xbitmap', 'xbitmap'):
	    imgtype = 'bitmap'
	else:
	    imgtype = 'photo'
	f = None
	tfn = tempfile.mktemp()
	try:
	    f = open(tfn, 'w')
	    BLOCKSIZE = 8*1024
	    try:
		while 1:
		    data = fp.read(BLOCKSIZE)
		    if not data: break
		    f.write(data)
	    except IOError, msg:
		print '*** IOError reading image', url, msg
		return None
	    f.close()
	    f = None
	    try:
		image = Image(imgtype, file=tfn)
	    except:
		print '***', url, 'does not appear to be of type', imgtype
		return None
	    self.image_cache[url] = image
	    return image
	finally:
	    fp.close()
	    if f:
		f.close()
	    try:
		os.unlink(tfn)
	    except os.error:
		pass

    def open_url(self, url, error=1):
	# Open a URL:
	# - return (fp, url) if successful
	# - display dialog and return (None, url) for errors
	#   (no dialog if errors argument is false)
	# - handle erro code 302 (redirect) silently
	try:
	    fp = self.urlopener.open(url)
	except IOError, msg:
	    if type(msg) == TupleType and len(msg) == 4:
		if msg[1] == 302:
		    m = msg[3]
		    if m.has_key('location'):
			url = m['location']
			return self.open_url(url)
		    elif m.has_key('uri'):
			url = m['uri']
			return self.open_url(url)
	    if error:
		self.error_dialog(IOError, msg)
	    fp = None
	content_type = None
	if fp:
	    headers = fp.info()
	    if headers:
		content_type = headers.type
	if not content_type:
	    content_type = self.guess_type(url)
	return fp, url, content_type

    def error_dialog(self, exc, msg):
	# Display an error dialog.
	# Return when the user clicks OK
	# XXX This looks horrible
	if type(msg) in (ListType, TupleType):
	    s = ''
	    for item in msg:
		s = s + ':\n' + str(item)
	    msg = s[2:]
	else:
	    msg = str(msg)
	SafeDialog.Dialog(self.root,
		      text=msg,
		      title=exc,
		      bitmap='error',
		      default=0,
		      strings=('OK',),
		      )

    def guess_type(self, url):
	"""Guess the type of a file based on its URL.

	Return value is a string of the form type/subtype, usable for
	a MIME Content-type header; or None if no type can be guessed.

	"""
	base, ext = posixpath.splitext(url)
	if self.extensions_map.has_key(ext):
	    return self.extensions_map[ext]
	elif self.extensions_map.has_key(string.lower(ext)):
	    return self.extensions_map[string.lower(ext)]
	else:
	    return None

    extensions_map = {
	'.html': 'text/html',
	'.htm': 'text/html',
	}


main()
