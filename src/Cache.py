"""Cache class.

XXX To do

- what if CacheItem.reset() fails?
- implement freshness check (needs some user prefs too)
- flush old cache items
- persistent cache
- probably need an interface to get the raw CacheItem instead of the
  CacheAPI instance, for the history list (which wants stuff cached
  even if the cache decides against it)
- etc.

"""


META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages


from assert import assert
import urlparse
import string
import os
import ni
import protocols


class Cache:

    """A cache of URL data.

    The open() method returns a cached version of whatever
    protocols.protocol_access() would return.

    """

    def __init__(self):
	self.cachedir = {}

    def open(self, url, mode, params, reload=0, data=None):
	key = self.url2key(url, mode, params)
	if data or not self.cachedir.has_key(key):
	    self.cachedir[key] = item = CacheItem(url, mode, params,
						  self, key, data)
##	    print "Cache.open() -> new item", item
	else:
	    item = self.cachedir[key]
##	    print "Cache.open() -> existing item", item
	    if reload:
		item.reset()
	    else:
		item.check()
	return CacheAPI(item)

    def delete(self, object):
	key = object.key
	object.cache = None
	assert(self.cachedir.has_key(key) and self.cachedir[key] is object)
	del self.cachedir[key]

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

    def __init__(self, url, mode, params, cache, key, data=None):
	self.refcnt = 0
	self.url = url
	self.mode = mode
	self.params = params
	self.cache = cache
	self.key = key
	self.postdata = data
	# The following two are changed by reset()
	self.api = None
	self.stage = DONE
	self.reset()

    def __repr__(self):
	return "CacheItem(%s)<%d>" % (`self.url`, self.refcnt)

    def incref(self):
	self.refcnt = self.refcnt + 1
##	print self, "incref() ->", self.refcnt

    def decref(self):
	assert(self.refcnt > 0)
	self.refcnt = self.refcnt - 1
##	print self, "decref() ->", self.refcnt
	if self.refcnt == 0:
	    if self.stage == DONE:
##		print "    finish()"
		self.finish()
	    else:
##		print "    abort()"
		self.abort()

    def check(self):
	if not self.fresh():
	    self.reset()

    def fresh(self):
	return self.stage is not DONE or self.complete

    def reset(self):
##	print self, "reset()"
	if self.stage != DONE:
	    return
	assert(self.api is None)
##	print "Open", self.url
	self.api = protocols.protocol_access(self.url,
					     self.mode, self.params,
					     data=self.postdata)
	self.meta = None
	self.data = ''
	self.stage = META
	self.complete = 0

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
		self.complete = 1
	    else:
		self.data = self.data + buf
	return self.data[offset:offset+maxbytes]

    def fileno(self):
	if self.api:
	    return self.api.fileno()
	else:
	    return -1

    def abort(self):
##	print " Abort", self.url
	if self.cache:
	    self.cache.delete(self)
	self.finish()

    def finish(self):
	if self.cache:
	    if not (self.meta and self.meta[0] == 200):
		self.cache.delete(self)
	self.stage = DONE
	api = self.api
	self.api = None
	if api:
##	    print "  Close", self.url
	    api.close()


class CacheAPI:

    """A thin interface to allow multiple threads to share a CacheItem.

    This has the same API as whatever protocol.protocol_access()
    returns.
    
    If the last CacheAPI is closed before the CacheItem has finished
    reading the data, the CacheItem removes itself from the Cache.

    """

    def __init__(self, item):
	self.item = item
	self.item.incref()
	self.offset = 0
	self.stage = META
	self.fno = -1
##	print self, "__init__()"

    def __repr__(self):
	return "CacheAPI(%s)" % self.item

    def __del__(self):
##	print self, "__del__()"
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

    def fileno(self):
	if self.fno < 0:
	    self.fno = self.item.fileno()
	    if self.fno >= 0:
		self.fno = os.dup(self.fno)
	return self.fno

    def close(self):
##	print self, "close()"
	self.stage = DONE
	fno = self.fno
	if fno >= 0:
	    self.fno = -1
	    os.close(fno)
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
