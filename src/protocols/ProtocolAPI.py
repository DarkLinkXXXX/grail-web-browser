"""Provisional Protocol API.

"""

import regsub
import string
from urllib import splittype


def protocol_access(url, mode, params):
    scheme, resturl = splittype(url)
    if not scheme:
	raise IOError, ("protocol error", "no scheme identifier in URL")
    scheme = string.lower(scheme)
    sanitized = regsub.gsub("[^a-zA-Z0-9]", "_", scheme)
    modname = sanitized + "API"
    try:
	m = __import__(modname)
    except ImportError:
	raise IOError, ("protocol error", "no support for %s" % scheme)
    classname = sanitized + "_access"
    if not hasattr(m, classname):
	raise IOError, ("protocol error", "incomplete support for %s" % scheme)
    klass = getattr(m, classname)
    return klass(resturl, mode, params)


def test(url = "http://www.python.org/"):
    import sys
    if sys.argv[1:]: url = sys.argv[1]
    api = protocol_access(url, 'GET', {})
    while 1:
	message, ready = api.pollmeta()
	print message
	if ready:
	    meta = api.getmeta()
	    print `meta`
	    break
    while 1:
	message, ready = api.polldata()
	print message
	if ready:
	    data = api.getdata(512)
	    print `data`
	    if not data:
		break
    api.close()


if __name__ == '__main__':
    test()
