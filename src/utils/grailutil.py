"""Miscellaneous utilities for Grail."""

__version__ = "$Revision: 2.6 $"
# $Source: /home/john/Code/grail/src/utils/grailutil.py,v $

import os

# XXX Unix specific stuff

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

def which(filename):
    import sys
    for dir in sys.path:
	found = os.path.join(dir, filename)
	if os.path.exists(found):
	    return found
    return None

def establish_dir(dir):
    """Ensure existence of DIR, creating it if necessary.

    Returns 1 if successful, 0 otherwise."""
    if os.path.isdir(dir):
	return 1
    try:
	if os.path.islink(dir):
	    curdir = os.path.getcwd()
	    os.chdir(dir)
	    os.chdir(curdir)
	    return 1
	elif os.path.exists(dir):
	    return 0
	else:
	    os.mkdir(dir, 0755)
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
