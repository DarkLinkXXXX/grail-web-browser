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
import mimetools
from Tkinter import *
import SafeDialog
import tktools
from Browser import Browser, DEFAULT_HOME
import SafeTkinter
from AppletRExec import AppletRExec
if 0:
    import dummies

# Milliseconds between interrupt checks
KEEPALIVE_TIMER = 200


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
    global app
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

    openers = {}			# XXX Should be in Application class
    
    def open_unknown(self, fullurl):
	type, url = urllib.splittype(fullurl)
	if self.openers.has_key(type):
	    opener = self.openers[type]
	else:
	    opener = self.find_extension(type)
	    if opener: self.openers[type] = opener
	if opener:
	    return opener(url)
	print "Unknown URL type:", type
	return urllib.URLopener.open_unknown(self, fullurl)

    def find_extension(self, type):
	# XXX Some of this needs to be moved into the Application class
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
	e = read_mime_types("/usr/local/etc/httpd/conf/mime.types") or \
	    read_mime_types("/usr/local/lib/netscape/mime.types") or {}
	for key, value in self.extensions_map.items():
	    if not e.has_key(key): e[key] = value
	self.extensions_map = e
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
	# - return (fp, url, content_type) if successful
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
	content_type = content_encoding = content_transfer_encoding = None
	if fp and hasattr(fp, 'info'):
	    headers = fp.info()
	    if headers:
		content_type = headers.gettype()
		content_encoding = headers.getheader('content-encoding')
		content_transfer_encoding = headers.getencoding()
	if fp and not content_type:
	    content_type, content_encoding = self.guess_type(url)
	# XXX content-transfer-encoding is not yet supported
##	if fp and content_transfer_encoding:
##	    fp = self.transfer_decode_pipeline(
##		fp, content_transfer_encoding, error)
	if fp and content_encoding:
	    fp = self.decode_pipeline(fp, content_encoding, error)
	return fp, url, content_type

    def decode_pipeline(self, fp, content_encoding, error=1):
	if self.decode_prog.has_key(content_encoding):
	    prog = self.decode_prog[content_encoding]
	    if not prog: return fp
	    tfn = tempfile.mktemp()
	    ok = 0
	    try:
		temp = open(tfn, 'w')
		BUFSIZE = 8192
		while 1:
			buf = fp.read(BUFSIZE)
			if not buf: break
			temp.write(buf)
		temp.close()
		ok = 1
	    finally:
		if not ok:
		    try:
			os.unlink(tfn)
		    except os.error:
			pass
	    pipeline = '%s <%s; rm -f %s' % (prog, tfn, tfn)
	    # XXX What if prog fails?
	    return os.popen(pipeline, 'r')
	if error:
	    self.error_dialog(IOError,
		"Can't decode content-encoding: %s" % content_encoding)
	return None

    decode_prog = {
	'gzip': 'gzip -d',
	'x-gzip': 'gzip -d',
	'compress': 'compress -d',
	'x-compress': 'compress -d',
	}

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
	if ext == '.tgz':
	    # Special case, can't be encoded in tables
	    base = base + '.tar'
	    ext = '.gz'
	if self.encodings_map.has_key(ext):
	    encoding = self.encodings_map[ext]
	    base, ext = posixpath.splitext(base)
	else:
	    encoding = None
	if self.extensions_map.has_key(ext):
	    return self.extensions_map[ext], encoding
	elif self.extensions_map.has_key(string.lower(ext)):
	    return self.extensions_map[string.lower(ext)], encoding
	else:
	    return 'text/plain', encoding

    encodings_map = {
	'.gz': 'gzip',
	'.Z': 'compress',
	}

    extensions_map = {
	'.a': 'application/octet-stream',
	'.ai': 'application/postscript',
	'.aif': 'audio/x-aiff',
	'.aifc': 'audio/x-aiff',
	'.aiff': 'audio/x-aiff',
	'.au': 'audio/basic',
	'.avi': 'video/x-msvideo',
	'.bcpio': 'application/x-bcpio',
	'.bin': 'application/octet-stream',
	'.cdf': 'application/x-netcdf',
	'.cpio': 'application/x-cpio',
	'.csh': 'application/x-csh',
	'.dvi': 'application/x-dvi',
	'.eps': 'application/postscript',
	'.etx': 'text/x-setext',
	'.gif': 'image/gif',
	'.gtar': 'application/x-gtar',
	'.hdf': 'application/x-hdf',
	'.htm': 'text/html',
	'.html': 'text/html',
	'.ief': 'image/ief',
	'.jpe': 'image/jpeg',
	'.jpeg': 'image/jpeg',
	'.jpg': 'image/jpeg',
	'.latex': 'application/x-latex',
	'.man': 'application/x-troff-man',
	'.me': 'application/x-troff-me',
	'.mif': 'application/x-mif',
	'.mov': 'video/quicktime',
	'.movie': 'video/x-sgi-movie',
	'.mpe': 'video/mpeg',
	'.mpeg': 'video/mpeg',
	'.mpg': 'video/mpeg',
	'.ms': 'application/x-troff-ms',
	'.nc': 'application/x-netcdf',
	'.o': 'application/octet-stream',
	'.oda': 'application/oda',
	'.pbm': 'image/x-portable-bitmap',
	'.pdf': 'application/pdf',
	'.pgm': 'image/x-portable-graymap',
	'.pnm': 'image/x-portable-anymap',
	'.ppm': 'image/x-portable-pixmap',
	'.ps': 'application/postscript',
	'.qt': 'video/quicktime',
	'.ras': 'image/x-cmu-raster',
	'.rgb': 'image/x-rgb',
	'.roff': 'application/x-troff',
	'.rtf': 'application/rtf',
	'.rtx': 'text/richtext',
	'.sgm': 'text/x-sgml',
	'.sgml': 'text/x-sgml',
	'.sh': 'application/x-sh',
	'.shar': 'application/x-shar',
	'.snd': 'audio/basic',
	'.so': 'application/octet-stream',
	'.src': 'application/x-wais-source',
	'.sv4cpio': 'application/x-sv4cpio',
	'.sv4crc': 'application/x-sv4crc',
	'.t': 'application/x-troff',
	'.tar': 'application/x-tar',
	'.tcl': 'application/x-tcl',
	'.tex': 'application/x-tex',
	'.texi': 'application/x-texinfo',
	'.texinfo': 'application/x-texinfo',
	'.tif': 'image/tiff',
	'.tiff': 'image/tiff',
	'.tr': 'application/x-troff',
	'.tsv': 'text/tab-separated-values',
	'.txt': 'text/plain',
	'.ustar': 'application/x-ustar',
	'.wav': 'audio/x-wav',
	'.xbm': 'image/x-xbitmap',
	'.xpm': 'image/x-xpixmap',
	'.xwd': 'image/x-xwindowdump',
	'.zip': 'application/zip',
	}


def read_mime_types(file):
    try:
	f = open(file)
    except IOError:
	return None
    map = {}
    while 1:
	line = f.readline()
	if not line: break
	words = string.split(line)
	for i in range(len(words)):
	    if words[i][0] == '#':
		del words[i:]
		break
	if not words: continue
	type, extensions = words[0], words[1:]
	for e in extensions:
	    map['.'+e] = type
    f.close()
    return map


main()
