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
