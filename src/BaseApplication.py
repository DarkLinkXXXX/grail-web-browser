"""Base class for the Grail Application object.

This provides the preferences initialization if needed as well as the
extension loading mechanisms.  The later are the primary motivation
for this, allowing the html2ps.py script to use extensions intelligently
using the same approaches (and implementation) as the Tk-based browser.
"""
__version__ = '$Revision: 2.7 $'
#  $Source: /home/john/Code/grail/src/BaseApplication.py,v $

import keyword
import os
import posixpath
import regsub
import string
import sys

import grailutil
import GrailPrefs

DEFAULT_DEVICE = 'viewer'		# should be 'writer', but this support
					# legacy HTML extensions


# downgrade the keyword module for 1.4 & older if needed:
try:
    exec "assert 1"
except SyntaxError:
    if "assert" in keyword.kwlist:
	keyword.kwlist.remove("assert")
	del keyword.kwdict["assert"]
    if not "access" in keyword.kwlist:
	keyword.kwlist.insert(0, "access")
	keyword.kwdict["access"] = 1


class BaseApplication:
    def __init__(self, prefs=None):
	grailutil._grail_app = self
	self.prefs = prefs or GrailPrefs.AllPreferences()
	self.graildir = grailutil.getgraildir()
	self.iconpath = [os.path.join(grailutil.get_grailroot(), 'icons')]
	self.get_package("html")	# make it a 'user' package
	grailutil.establish_dir(self.graildir)
	s = \
	  read_mime_types(os.path.join(self.graildir, "mime.types")) or \
	  read_mime_types("/usr/local/lib/netscape/mime.types") or \
	  read_mime_types("/usr/local/etc/httpd/conf/mime.types") or \
	  {}
	for key, value in self.suffixes_map.items():
	    if not s.has_key(key): s[key] = value
	self.suffixes_map = s
	user_icons = os.path.join(self.graildir, 'icons')
	if os.path.isdir(user_icons):
	    self.iconpath.insert(0, user_icons)
	# cache of available extensions
	self.__extensions = {}

    # Mapping '.' to os.sep to test for the user dir is needed to support
    # nested packages.
    __pkg2path_map = string.maketrans('.', os.sep)
    def get_package(self, name):
	exec "import %s; package = %s" % (name, name)
	userdir = os.path.join(self.graildir,
			       string.translate(name, self.__pkg2path_map))
	if os.path.isdir(userdir) and userdir not in package.__path__:
	    package.__path__.insert(0, userdir)
	return package

    def get_package_module(self, pkgname, modname):
	package = self.get_package(pkgname) # make it a 'user' package
	if not package:
	    return None
	if keyword.iskeyword(modname):
	    modname = modname + "_"
	exec "from %s import %s; mod = %s" % (pkgname, modname, modname)
	return mod

    def find_embedder(self, devicetype, mimetype):
	modname, mod = self.find_type_extension("obj_" + devicetype, mimetype)
	if modname:
	    name = "embed_" + modname
	    if hasattr(mod, name):
		return getattr(mod, name)
	return None

    def find_type_extension(self, package, mimetype):
	try:
	    content_type, opts = grailutil.conv_mimetype(mimetype)
	except:
	    return None, None
	[type, subtype] = string.splitfields(content_type, '/')
	type = regsub.gsub("[^a-zA-Z0-9_]", "_", type)
	subtype = regsub.gsub("[^a-zA-Z0-9_]", "_", subtype)
	result = None, None
	for modname in (type + "_" + subtype, type):
	    mod = self.find_extension(package, modname)
	    if mod:
		return modname, mod
	return None, None

    __tagmask = string.maketrans('-.', '__')
    def find_html_extension(self, tag, device):
	tag = string.translate(tag, self.__tagmask)
	if not self.__have_taginfo(tag, device):
	    mod = self.find_extension("html", tag)
	    if mod:
		self.load_tag_handlers(mod)
	if self.__have_taginfo(tag, device):
	    return self.__get_taginfo(tag, device)
	return None

    def load_tag_handlers(self, mod):
	as_list = 1
	if hasattr(mod, "ATTRIBUTES_AS_KEYWORDS"):
	    as_list = not mod.ATTRIBUTES_AS_KEYWORDS
	handlers = {}
	for name in dir(mod):
	    parts = string.splitfields(name, "_")
	    if len(parts) not in (2, 3):
		continue
	    if not (parts[-2] and parts[-1] and parts[0]):
		continue
	    if len(parts) == 2:
		device = DEFAULT_DEVICE
		[action, tag] = parts
	    else:
		[device, action, tag] = parts
	    start = do = end = None
	    if handlers.has_key((tag, device)):
		start, do, end = handlers[(tag, device)]
	    if action == 'start':
		start = getattr(mod, name)
		if as_list:
		    start = ListAttributesCaller(start)
	    elif action == 'end':
		end = getattr(mod, name)
	    elif action == 'do':
		do = getattr(mod, name)
		if as_list:
		    do = ListAttributesCaller(do)
	    handlers[(tag, device)] = (start, do, end)
	from SGMLParser import TagInfo
	for (tag, device), (start, do, end) in handlers.items():
	    if start or do:
		taginfo = TagInfo(tag, start, do, end)
		self.__taginfo[(tag, device)] = taginfo

    __taginfo = {}
    def __get_taginfo(self, tag, device):
	return self.__taginfo[(tag, device)]

    def __have_taginfo(self, tag, device):
	return self.__taginfo.has_key((tag, device))

    def find_extension(self, subdir, module):
	key = (subdir, module)
	if self.__extensions.has_key(key):
	    return self.__extensions[key]
	mod = None
	try:
	    mod = self.get_package_module(subdir, module)
	except ImportError:
	    pass
	except:
	    self.exception_dialog("while importing %s.%s" % (subdir, module))
	self.__extensions[key] = mod
	return mod

    #######################################################################
    #
    #  Misc. support.
    #
    #######################################################################

    def exception_dialog(self, message="", *args):
	raise RuntimeError, "Subclass failed to implement exception_dialog()."

    import regex
    __data_scheme_re = regex.compile(
	"data:\([^,;]*\)\(;\([^,]*\)\|\),", regex.casefold)
    def guess_type(self, url):
	"""Guess the type of a file based on its URL.

	Return value is a string of the form type/subtype, usable for
	a MIME Content-type header; or None if no type can be guessed.

	"""
	if self.__data_scheme_re.match(url) >= 0:
	    scheme = self.__data_scheme_re.group(1) or "text/plain"
	    return string.lower(scheme), self.__data_scheme_re.group(3)
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
	return None, encoding

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
	'.png': 'image/png',
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


def _nullfunc(*args, **kw):
    pass


class ListAttributesCaller:
    """Call a tag handler function, translating the attributes dictionary to
    a list.

    This is useful for legacy HTML tag extensions.  The SGML & HTML support
    in Grail never has to see attributes as lists; simplifying and supporting
    a number of automatic value normalizations (esp. URI normalization and ID/
    IDREF support).
    """
    def __init__(self, func):
	self.__func = func

    def __call__(self, parser, attrs):
	return apply(self.__func, (parser, attrs.items()))

#
#  end of file
