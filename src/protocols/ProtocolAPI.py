"""Protocol API -- with proxy support.

Proxy support is controlled by a set of environment variables: for
each protocol, there's

	<scheme>_proxy=<url>

e.g.

	ftp_proxy=http://proxysvr.local.com:8080

The protocol API module that is used to communicate to the proxy
server (in the example, module httpAPI) must accept a url parameter
that is a tuple of the form (hostport, selector) where hostport is the
host and port of the proxy server (in the example,
"proxysvr.local.com:8080") and selector is the full URL to be sent to
the proxy.  Currently, only the httpAPI module supports this.  (With
non-proxy usage, the url parameter is a string.)

"""


import regsub
import string
from urllib import splittype, splithost, splitport


def protocol_access(url, mode, params, data=None):
    scheme, resturl = splittype(url)
    if not scheme:
	raise IOError, ("protocol error", "no scheme identifier in URL")
    scheme = string.lower(scheme)
    sanitized = regsub.gsub("[^a-zA-Z0-9]", "_", scheme)
    proxy = getenv(sanitized + "_proxy")
    if proxy:
	do_proxy = 1
	no_proxy = getenv("no_proxy")
	if no_proxy:
	    list = map(string.strip, string.split(no_proxy, ","))
	    url_host, url_remains = splithost(resturl)
	    url_host = string.lower(url_host)
	    if url_host in list:
		do_proxy = 0
	    else:
		url_host, url_port = splitport(url_host)
		if url_host in list:
		    do_proxy = 0
	if do_proxy:
	    proxy_scheme, proxy_resturl = splittype(proxy)
	    proxy_host, proxy_remains = splithost(proxy_resturl)
	    resturl = (proxy_host, url)
	    scheme = string.lower(proxy_scheme)
	    sanitized = regsub.gsub("[^a-zA-Z0-9]", "_", scheme)
	    print "Sending", url
	    print "     to", scheme, "proxy", proxy_host
    modname = sanitized + "API"
    try:
	m = __import__(modname)
    except ImportError:
	m = None
    if not m:
	raise IOError, ("protocol error", "no support for %s" % scheme)
    classname = sanitized + "_access"
    if not hasattr(m, classname):
	raise IOError, ("protocol error", "incomplete support for %s" % scheme)
    klass = getattr(m, classname)
    if data:
	return klass(resturl, mode, params, data)
    else:
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


def getenv(name):
    import os
    try:
	return os.environ[name]
    except:
	return None


if __name__ == '__main__':
    test()
