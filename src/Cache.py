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

CacheItemExpired = 'CacheItem Expired'


from assert import assert
import urlparse
import string
import regsub
import os
import protocols
import time
import copy

class OldCache:

    """A cache of URL data.

    The open() method returns a cached version of whatever
    protocols.protocol_access() would return.

    """

    def __init__(self,app):
	self.cachedir = {}
	self.app = app

	###
	###  hard-coded values follow
	###  they are for development only
	###  I need to figure out the preferences interface
	###
	self.cache_manager = CacheManager()
	disk = DiskCache( self.cache_manager, 1000000, 
			  self.app.graildir + '/cache' )


#
# potentially different cases for open
#    should we handle POSTs differently than gets
#
#
#

    def open(self, url, mode, params, reload=0, data=None):
	if mode == 'GET':
	    return self.get(url, mode, params, reload, data)
	elif mode == 'POST':
	    return self.post(url, mode, params, reload, data)

    def OLDopen(self, url, mode, params, reload=0, data=None):
	### do we decide here to avoid the cache for POST?
	### the non-idempotent nature of POST may mean yes
	if data:
	    return CacheAPI(CacheItem(url, mode, params, self, key, data))

	key = self.url2key(url, mode, params)
	api = self.cache_manager.get(key)
	if api:
	    item = CacheItem(url, mode, params,
			     self, key, data, api)
	    if reload:
		item.reset(reload) # force a reload
	    else:
		item.check() # check for freshness
	else:
	    item = CacheItem(url, mode, params,
			     self, key, data)
	return CacheAPI(item)

    def post(self, url, mode, params, reload, data):
	# for now, never cache a POST
	key = self.url2key(url, mode, params)
	return CacheAPI(CacheItem(url, mode, params, None, key, data))

    def get(self, url, mode, params, reload, data):
	key = self.url2key(url, mode, params)
	api = self.cache_manager.get(key)
	if api:
	    # creating reference to cached item
	    try:
		item = CacheItem(url, mode, params, self, key, data, api)
	    except CacheItemExpired:
		self.cache_manager.evict(key)
	    if reload:
		item.reset(reload)
	    else:
		item.check() # check for freshness
	else:
	    # cause item to be loaded (and perhaps cached)
	    item = CacheItem(url, mode, params, self, key, data)
	return CacheAPI(item)

    def delete(self, object):
	key = object.key
	object.cache = None
#	assert(self.cachedir.has_key(key) and self.cachedir[key] is object)
#	del self.cachedir[key]

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

    A CacheItem hides all protocol access from the rest of the
    system. The reset() method actually calls on the protocol to
    retrieve an object.

    The disk cache passes an disk_cache_access api which sets some
    basic headers and starts the object out in the DATA state.

    """

    def __init__(self, url, mode, params, cache, key, data=None,
		 api=None, last_load=None):  
	self.refcnt = 0
	self.url = url
	self.mode = mode
	self.params = params
	self.key = key
	self.postdata = data
	self.reloading = 0
	self.cache = cache

	if api:
	    # loading from the cache
	    self.api = api
	    self.meta = api.getmeta()
	    self.stage = self.api.stage
	    self.data = ''
	    self.complete = 0
	    self.incache = 1
	    if last_load:
		self.refresh(last_load)
	else:
	    # The following two are changed by reset()
	    self.api = None
	    self.stage = DONE
	    self.stored = None  # not used for anything?
	    self.incache = 0
	    self.reset()

    def __repr__(self):
	return "CacheItem(%s)<%d>" % (`self.url`, self.refcnt)

    def iscached(self):
	return self.incache

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

    def reset(self,reload=0):
	if self.incache == 0:
	    if self.stage != DONE:
		return
	    assert(self.api is None)
	self.api = protocols.protocol_access(self.url,
					     self.mode, self.params,
					     data=self.postdata)
	self.init_new_load()
	self.reloading = reload

    def init_new_load(self):
	self.meta = None
	self.data = ''
	self.stage = META
	self.complete = 0

    def refresh(self,when):
	if self.incache == 1:
	    # can only refresh something in the cache
	    # should we ignore this test?
	    params = copy.copy(self.params)
	    params['If-Modified-Since'] = when.get_str()
	    api = protocols.protocol_access(self.url,
					    self.mode, params,
					    data=self.postdata)
	    errcode, errmsg, headers = api.getmeta()
	    ### which errcode should I try to handle
	    if errcode == 304:
		# we win! it hasn't been modified
##		print "if-mod-since reports no change"
		pass
	    elif errcode == 200:
##		print "if-mod-since returned new page"
		self.api = api
		self.init_new_load()
		self.reloading = 1
	    else:
		print "an if-mod-since returned %s, %s" % (errcode, errmsg)

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
	    # don't put this baby in the cache
	    self.cache = None
	self.finish()

    def finish(self):
	if self.cache:
	    if not (self.meta and self.meta[0] == 200):
		self.cache.delete(self)
	    elif (self.incache == 0 or self.reloading == 1) \
		 and not self.postdata and self.refcnt == 0:
#		 and not self.postdata and self.complete == 0:
		self.cache.add(self,self.reloading)
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

    def iscached(self):
	return self.item.iscached()

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
#	print self, "close()"
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
