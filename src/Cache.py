"""Cache class.

XXX To do

- what if CacheItem.reset() fails?
- need to implement freshness check (needs some user prefs too)
- persistent cache
- probably need an interface to get the raw CacheItem instead of the
  CacheAPI instance, for the history list (which wants stuff cached
  even if the cache decides against it)
- need an interface to force reloads
- etc.

"""


META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages


from assert import assert
import urlparse
import string
import ProtocolAPI


class Cache:

    """A cache of URL data.

    The open() method returns a cached version of whatever
    ProtocolAPI.protocol_access() would return.

    """

    def __init__(self):
	self.cachedir = {}

    def open(self, url, mode, params):
	reload = params.has_key('.reload') and params['.reload']
	key = self.url2key(url, mode, params)
	if not self.cachedir.has_key(key):
	    self.cachedir[key] = item = CacheItem(url, mode, params, self, key)
	else:
	    item = self.cachedir[key]
	    if reload:
		item.reset()
	    else:
		item.check()
	return CacheAPI(item)

    def url2key(self, url, mode, params):
	"""Normalize a URL for use as a caching key.

	- change the hostname to all lowercase
	- remove the port if it is the scheme's default port
	- reformat the port using %d
	- get rid of the fragment identifier

	XXX Questions

	- how do we know the scheme's default port?
	- do we need mode, params?
	- should we default the scheme to http?
	- should we default the netloc to localhost?
	- should we equivalence file and ftp schemes?
	- should we lowercase the scheme?
	- should we change the hostname to numeric form to catch DNS aliases?
	  (but what about round-robin DNS?)

	"""
	scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
	i = string.find(netloc, '@')
	if i > 0:
	    userpass = netloc[:i]
	    netloc = netloc[i:]
	else:
	    userpass = ""
	i = string.find(netloc, ':')
	if i >= 0:
	    try:
		port = string.atoi(netloc[i+1:])
	    except string.atoi_error:
		port = None
	else:
	    port = None
	if scheme == 'http' and port == 80:
	    netloc = netloc[:i]
	elif type(port) == type(0):
	    netloc = netloc[:i] + ":%d" % port
	return urlparse.urlunparse((scheme, netloc, path, params, query, ""))


class CacheItem:

    """A shareable cache item.

    The interface is subtly different from that of protocol objects:
    getdata() takes an offset argument, and the sequencing
    restrictions are lifted (i.e. you can call anything in any order).

    """

    def __init__(self, url, mode, params, cache, key):
	self.refcnt = 0
	self.url = url
	self.mode = mode
	self.params = params
	self.cache = cache
	self.key = key
	self.reset()

    def incref(self):
	self.refcnt = self.refcnt + 1

    def decref(self):
	assert(self.refcnt > 0)
	self.refcnt = self.refcnt - 1
	if self.refcnt == 0:
	    if self.stage == DONE:
		self.finish()
	    else:
		self.abort()

    def check(self):
	if not self.fresh():
	    self.reset()

    def fresh(self):
	return 1

    def reset(self):
	self.api = ProtocolAPI.protocol_access(self.url,
					       self.mode, self.params)
	self.meta = None
	self.data = ''
	self.stage = META

    def pollmeta(self):
	if self.stage == META:
	    return self.api.pollmeta()
	elif self.stage == DATA:
	    return self.api.polldata()[0], 1
	else:
	    return "Reading cache", 1

    def getmeta(self):
	if self.stage == META:
	    self.meta = self.api.getmeta()
	    self.stage = DATA
	return self.meta

    def polldata(self):
	if self.stage == META:
	    msg, ready = self.api.pollmeta()
	    if ready:
		self.getmeta()
		msg, ready = self.api.polldata()
	elif self.stage == DATA:
	    msg, ready = self.api.polldata()
	else:
	    msg, ready = "Reading cache", 1
	return msg, ready

    def getdata(self, offset, maxbytes):
	assert(offset >= 0)
	assert(maxbytes > 0)
	if self.stage == META:
	    self.meta = self.api.getmeta()
	    self.stage = DATA
	while self.stage == DATA and offset >= len(self.data):
	    buf = self.api.getdata(maxbytes)
	    if not buf:
		self.finish()
	    else:
		self.data = self.data + buf
	return self.data[offset:offset+maxbytes]

    def abort(self):
	if self.cache:
	    cachedir = self.cache.cachedir
	    key = self.key
	    assert(cachedir.has_key(key) and self is cachedir[key])
	    del cachedir[key]
	self.finish()

    def finish(self):
	self.stage = DONE
	self.cache = None
	api = self.api
	self.api = None
	if api:
	    api.close()


class CacheAPI:

    """A thin interface to allow multiple threads to share a CacheItem.

    This has the same API as whatever ProtocolAPI.protocol_access()
    returns.
    
    If the last CacheAPI is closed before the CacheItem has finished
    reading the data, the CacheItem removes itself from the Cache.

    """

    def __init__(self, item):
	self.item = item
	self.item.incref()
	self.offset = 0
	self.stage = META

    def __del__(self):
	self.close()

    def pollmeta(self):
	assert(self.stage == META)
	return self.item.pollmeta()

    def getmeta(self):
	assert(self.stage == META)
	meta = self.item.getmeta()
	self.stage = DATA
	return meta

    def polldata(self):
	assert(self.stage == DATA)
	return self.item.polldata()

    def getdata(self, maxbytes):
	assert(self.stage == DATA)
	data = self.item.getdata(self.offset, maxbytes)
	self.offset = self.offset + len(data)
	if not data:
	    self.close()
	return data

    def close(self):
	self.stage = DONE
	item = self.item
	if item:
	    self.item = None
	    item.decref()


def test():
    """Simple test program."""
    import sys
    url = "http://www.python.org/"
    if sys.argv[1:]: url = sys.argv[1]
    c = Cache()
    for i in range(3):
	api = c.open(url, 'GET', {})
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
