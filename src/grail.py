#! /depot/sundry/plat/bin/python


"""Grail -- an extensible web browser.

"""


# Version string in a form ready for the User-agent HTTP header
__version__ = "Grail/0.2.2"		# 0.2 plus fixes plus <applet> tag


import sys
import os

# Hack sys.path:
# replace the last occurrence of curdir or "" by dirname of argv[0]
progname = sys.argv[0]
dirname = os.path.dirname(progname)
if dirname and dirname != os.curdir:
    index = -1
    for i in range(len(sys.path)):
	p = sys.path[i]
	if p in ("", os.curdir):
	    index = i
    if index >= 0:
	sys.path[index] = dirname
    else:
	sys.path.insert(0, dirname)

from grailutil import *
import getopt
import string
import urllib
import tempfile
import posixpath
import traceback
import mimetools
from Tkinter import *
import SafeDialog
import tktools
from Browser import Browser, DEFAULT_HOME
import SafeTkinter
from AppletRExec import AppletRExec
from Cache import Cache
import TbDialog
if 0:
    import dummies
import GlobalHistory

# Milliseconds between interrupt checks
KEEPALIVE_TIMER = 500

# Location of logo image for splash screen
BIGLOGO = "biglogo.gif"

# Notice displayed underneath the big logo
NOTICE = """Copyright \251 1995
Corporation for National
Research Initiatives

Version: %s""" % __version__


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
    browser = Browser(app.root, app, geometry=geometry)
    if url:
	app.home = url
    if sys.platform != 'mac':
    	browser.load(app.home)
    SafeTkinter._castrate(app.root.tk)
    tktools.install_keybindings(app.root)
    # Make everybody who's still using urllib.urlopen go through the cache
    urllib.urlopen = app.open_url_simple
    # Add $GRAILDIR/user/ to sys.path
    subdir = os.path.join(app.graildir, 'user')
    if subdir not in sys.path:
	sys.path.insert(0, subdir)
    # Import user's grail startup file, defined as
    # $GRAILDIR/user/grailrc.py if it exists.
    try: import grailrc
    except ImportError: pass
    except:
	app.exception_dialog('during import of startup file')
    app.go()


class SplashScreen:

    """Display splash screen at startup.

    This uses the initial Tk widget.
    It goes away after 10 seconds.

    """

    def __init__(self, root):
	self.root = root
	self.frame = Frame(self.root)
	self.frame.pack()
	for dir in sys.path:
	    fullname = os.path.join(dir, BIGLOGO)
	    try:
		f = open(fullname)
	    except IOError:
		pass
	    else:
		f.close()
		break
	else:
	    fullname = BIGLOGO
	self.image = PhotoImage(file=fullname)
	self.label = Label(self.frame, image=self.image)
	self.label.pack()
	self.message = Label(self.frame, text=NOTICE)
	self.message.pack()
	screenwidth = self.root.winfo_screenwidth()
	screenheight = self.root.winfo_screenheight()
	reqwidth = self.image.width()
	reqheight = self.image.height()
	xpos = (screenwidth - reqwidth) / 2
	ypos = (screenheight - reqheight) / 2
	self.root.geometry("+%d+%d" % (xpos, ypos))
	name = "Grail"
	self.root.title(name)
	self.root.iconname(name)
	self.root.update_idletasks()
	self.root.after(10000, self.close)

    def close(self):
	self.frame.destroy()
	self.root.withdraw()


class URLReadWrapper:

    def __init__(self, api, meta):
	self.api = api
	self.meta = meta
	self.eof = 0

    def read(self, nbytes=-1):
	buf = ''
	BUFSIZ = 8*1024
	while nbytes != 0 and not self.eof:
	    new = self.api.getdata(nbytes < 0 and BUFSIZ or nbytes)
	    if not new:
		self.eof = 1
		break
	    buf = buf + new
	    if nbytes > 0:
		nbytes - nbytes - len(new)
		if nbytes <= 0:
		    break
	return buf

    def info(self):
	return self.meta

    def close(self):
	api = self.api
	self.api = None
	self.meta = None
	if api:
	    api.close()


class Application:

    """The application class represents a group of browser windows."""

    def __init__(self):
	self.root = Tk(className='Grail')
	self.splash = SplashScreen(self.root)
	self.load_images = 1
	self.home = DEFAULT_HOME
	# initialize on_exit_methods before global_history
	self.on_exit_methods = []
	self.global_history = GlobalHistory.GlobalHistory(self)
	self.url_cache = Cache()
	self.image_cache = {}
	self.login_cache = {}
	self.rexec = AppletRExec(None, 2, self)
	self.graildir = getgraildir()
	s = \
	  read_mime_types(os.path.join(self.graildir, "mime.types")) or \
	  read_mime_types("/usr/local/lib/netscape/mime.types") or \
	  read_mime_types("/usr/local/etc/httpd/conf/mime.types") or \
	  {}
	for key, value in self.suffixes_map.items():
	    if not s.has_key(key): s[key] = value
	self.suffixes_map = s
	self.root.report_callback_exception = self.report_callback_exception
	self.keep_alive()
	self.browsers = []

    def register_on_exit(self, method):
	self.on_exit_methods.append(method)
    def unregister_on_exit(self, method):
	try: self.on_exit_methods.remove(method)
	except ValueError: pass
    def exit_notification(self):
	for m in self.on_exit_methods[:]:
	    try: m()
	    except: pass

    def add_browser(self, browser): self.browsers.append(browser)
    def del_browser(self, browser):
	try: self.browsers.remove(browser)
	except ValueError: pass

    def quit(self):
	self.root.destroy()

    def maybe_quit(self):
	if not self.root.children:
	    self.quit()

    def go(self):
	try:
	    self.root.mainloop()
	except KeyboardInterrupt:
	    pass
	self.exit_notification()

    def keep_alive(self):
	# Exercise the Python interpreter regularly so keyboard
	# interrupts get through
	self.root.tk.createtimerhandler(KEEPALIVE_TIMER, self.keep_alive)

    html_start_tags = {}
    html_end_tags = {}

    def find_html_start_extension(self, tag):
	if self.html_start_tags.has_key(tag):
	    return self.html_start_tags[tag]
	mod = self.find_extension('html', tag)
	if not mod:
	    self.html_start_tags[tag] = None
	    return None
	for name in dir(mod):
	    if name[:6] == 'start_':
		t = name[6:]
		if t and not self.html_start_tags.has_key(t):
		    self.html_start_tags[t] = getattr(mod, name)
	    elif name[:4] == 'end_':
		t = name[4:]
		if t and not self.html_end_tags.has_key(t):
		    self.html_end_tags[t] = getattr(mod, name)
	    elif name[:3] == 'do_':
		t = name[3:]
		if t and not self.html_start_tags.has_key(t):
		    self.html_start_tags[t] = getattr(mod, name)
	if not self.html_start_tags.has_key(tag):
	    print "Hmm... module html/%s doesn't define start_%s" % (tag, tag)
	    self.html_start_tags[tag] = None
	return self.html_start_tags[tag]

    def find_html_end_extension(self, tag):
	if self.html_end_tags.has_key(tag):
	    return self.html_end_tags[tag]
	else:
	    return None

    def get_cached_image(self, url):
	if url and self.image_cache.has_key(url):
	    return self.image_cache[url]
	else:
	    return None

    def set_cached_image(self, url, image):
	self.image_cache[url] = image

    def open_url(self, url, method, params, reload=0, data=None):
	api = self.url_cache.open(url, method, params, reload, data=data)
	api._url_ = url
	return api

    def open_url_simple(self, url):
	api = self.open_url(url, 'GET', {})
	errcode, errmsg, meta = api.getmeta()
	if errcode != 200:
	    raise IOError, ('url open error', errcode, errsmg, meta)
	return URLReadWrapper(api, meta)

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

    def find_extension(self, subdir, module):
	oldpath = sys.path
	newpath = oldpath[:]
	subdir = os.path.join(self.graildir, subdir)
	if subdir not in newpath:
	    newpath.insert(0, subdir)
	try:
	    try:
		sys.path = newpath
		return __import__(module)
	    finally:
		sys.path = oldpath
	except ImportError:
	    return None
	except:
	    self.exception_dialog("while importing %s" % module)
	    return None

    def exception_dialog(self, message=""):
	exc, val, tb = sys.exc_type, sys.exc_value, sys.exc_traceback
	self.exc_dialog(message, exc, val, tb)

    def report_callback_exception(self, exc, val, tb):
	self.exc_dialog("in a callback function", exc, val, tb)

    def exc_dialog(self, message, exc, val, tb):
	def f(s=self, m=message, e=exc, v=val, t=tb):
	    s._exc_dialog(m, e, v, t)
	if TkVersion >= 4.1:
	    self.root.after_idle(f)
	else:
	    self.root.after(0, f)

    def _exc_dialog(self, message, exc, val, tb):
	# XXX This needn't be a modal dialog --
	# XXX should SafeDialog be changed to support callbacks?
	msg = "An exception occurred " + str(message) + " :\n"
	msg = msg + str(exc) + " : " + str(val)
	dlg = SafeDialog.Dialog(self.root,
				text=msg,
				title="Python Exception: " + str(exc),
				bitmap='error',
				default=0,
				strings=("OK", "Show traceback"),
				)
	if dlg.num == 1:
	    self.traceback_dialog(exc, val, tb)

    def traceback_dialog(self, exc, val, tb):
	# XXX This could actually just create a new Browser window...
	TbDialog.TracebackDialog(self.root, exc, val, tb)

    def error_dialog(self, exc, msg, root=None):
	# Display an error dialog.
	# Return when the user clicks OK
	# XXX This needn't be a modal dialog
	if type(msg) in (ListType, TupleType):
	    s = ''
	    for item in msg:
		s = s + ':\n' + str(item)
	    msg = s[2:]
	else:
	    msg = str(msg)
	SafeDialog.Dialog(root or self.root,
		      text=msg,
		      title="Error: " + str(exc),
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
	if ext in ('.tgz', '.taz', '.tz'):
	    # Special case, can't be encoded in tables
	    base = base + '.tar'
	    ext = '.gz'
	if self.encodings_map.has_key(ext):
	    encoding = self.encodings_map[ext]
	    base, ext = posixpath.splitext(base)
	else:
	    encoding = None
	if self.suffixes_map.has_key(ext):
	    return self.suffixes_map[ext], encoding
	elif self.suffixes_map.has_key(string.lower(ext)):
	    return self.suffixes_map[string.lower(ext)], encoding
	else:
	    return 'text/plain', encoding

    encodings_map = {
	'.gz': 'gzip',
	'.Z': 'compress',
	}

    suffixes_map = {
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
	'.dll': 'application/octet-stream',
	'.dvi': 'application/x-dvi',
	'.exe': 'application/octet-stream',
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
	'.obj': 'application/octet-stream',
	'.oda': 'application/oda',
	'.pbm': 'image/x-portable-bitmap',
	'.pdf': 'application/pdf',
	'.pgm': 'image/x-portable-graymap',
	'.pnm': 'image/x-portable-anymap',
	'.ppm': 'image/x-portable-pixmap',
	'.py': 'text/x-python',
	'.pyc': 'application/x-python-code',
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
	type, suffixes = words[0], words[1:]
	for suff in suffixes:
	    map['.'+suff] = type
    f.close()
    return map


if sys.argv[1:] and sys.argv[1][:2] == '-p':
    p = sys.argv[1]
    del sys.argv[1]
    if p[2:]: n = eval(p[2:])
    else: n = 20
    import profile
    profile.run('main()', '@grail.prof')
    import pstats
    p = pstats.Stats('@grail.prof')
    p.strip_dirs().sort_stats('time').print_stats(n)
    p.print_callers(n)
    p.strip_dirs().sort_stats('cum').print_stats(n)
else:
    main()
