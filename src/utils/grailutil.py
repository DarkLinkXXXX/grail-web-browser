"""Miscellaneous utilities for Grail."""

__version__ = "$Revision: 2.11 $"
# $Source: /home/john/Code/grail/src/utils/grailutil.py,v $

import os

# XXX Unix specific stuff
# XXX (Actually it limps along just find for Macintosh, too)

def getgraildir():
    return getenv("GRAILDIR") or os.path.join(gethome(), ".grail")

def gethome():
    try:
	home = getenv("HOME")
	if not home:
	    import pwd
	    user = getenv("USER") or getenv("LOGNAME")
	    if not user:
		pwent = pwd.getpwuid(os.getuid())
	    else:
		pwent = pwd.getpwnam(user)
	    home = pwent[6]
	return home
    except (KeyError, ImportError):
	return os.curdir

def getenv(s):
    if os.environ.has_key(s): return os.environ[s]
    return None

def which(filename, searchlist=None):
    if searchlist is None:
	import sys
	searchlist = sys.path
    for dir in searchlist:
	found = os.path.join(dir, filename)
	if os.path.exists(found):
	    return found
    return None

def establish_dir(dir):
    """Ensure existence of DIR, creating it if necessary.

    Returns 1 if successful, 0 otherwise."""
    if os.path.isdir(dir):
	return 1
    head, tail = os.path.split(dir)
    if not establish_dir(head):
	return 0
    try:
	os.mkdir(dir, 0777)
	return 1
    except os.error:
	return 0

def complete_url(url):
    import urlparse
    scheme, netloc = urlparse.urlparse(url)[:2]
    if not scheme:
	if not netloc:
	    # XXX url2pathname/pathname2url???
	    if os.path.exists(url):
		import urllib
		url = "file:" + urllib.quote(url)
	    else:
		url = "http://" + url
	else:
	    url = "http:" + url
    return url

def nicebytes(n):
    """Convert a bytecount to a string like '<number> bytes' or '<number>K'.

    This is intended for inclusion in status messages that display
    things like '<number>% read of <bytecount>' or '<bytecount> read'.
    When the byte count is large, it will be expressed as a small
    floating point number followed by K, M or G, e.g. '3.14K'.

    The word 'bytes' (or singular 'byte') is part of the returned
    string if the byte count is small; when the count is expressed in
    K, M or G, 'bytes' is implied.

    """
    if n < 1000:
	if n == 1: return "1 byte"
	return "%d bytes" % n
    n = n * 0.001
    if n < 1000.0:
	suffix = "K"
    else:
	n = n * 0.001
	if n < 1000.0:
	    suffix = "M"
	else:
	    n = n * 0.001
	    suffix = "G"
    if n < 10.0: r = 2
    elif n < 100.0: r = 1
    else: r = 0
    return "%.*f" % (r, n) + suffix



import string

# HTML utilities.  This should maybe go someplace else, but it should
# definitely be a function and not a method of some class.

def extract_attribute(key, dict, default=None, conv=None, delete=1):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function, and
    DELETE (if true) says to delete the extracted key from the
    dictionary upon successful extraction.

    """
    if dict.has_key(key):
	val = dict[key]
	if delete:
	    del dict[key]
	if not conv:
	    return val
	try:
	    return conv(val)
	except:
	    return default
    return default

def extract_keyword(key, dict, default=None, conv=None):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function.
    """
    if dict.has_key(key):
	if conv:
	    try:
		return conv(dict[key])
	    except:
		return default
	return dict[key]
    return default

def conv_integer(val, conv=string.atoi, otherlegal=''):
    val = string.strip(val)
    l = len(val)
    start = 0
    if val[0] in '+-':
	start = 1
    legalchars = string.digits + otherlegal
    for i in range(start, l):
	if val[i] not in legalchars:
	    val = val[:i]
	    break
    return conv(val)

def conv_float(val):
    return conv_integer(val, conv=string.atof, otherlegal='.')

def conv_normstring(val):
    return string.lower(string.strip(val))

def conv_enumeration(val, mapping_or_list):
    if type(mapping_or_list) == type([]):
	if val in mapping_or_list: return val
	else: return None
    else:
	if mapping_or_list.has_key(val): return mapping_or_list[val]
	else: return None

def conv_exists(val):
    return 1
