"""Cache class.

XXX To do

- probably need an interface to get the raw CacheItem instead of the
  CacheAPI instance, for the history list (which wants stuff cached
  even if the cache decides against it)
"""

META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages

CacheItemExpired = 'CacheItem Expired'

from assert import assert
import os
import protocols
import time
import copy

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
	    self.data = []
	    self.datalen = 0
	    self.datamap = {}
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
	return self.incache and not self.reloading

    def incref(self):
	self.refcnt = self.refcnt + 1

    def decref(self):
	assert(self.refcnt > 0)
	self.refcnt = self.refcnt - 1
	self.cache_update()
	if self.refcnt == 0:
	    if self.stage == DONE:
		self.finish()
	    else:
		self.abort()

    def cache_update(self):
	if (self.incache == 0 or self.reloading == 1) \
	   and not self.postdata and self.complete == 1 \
	   and (self.meta and self.meta[0] == 200):
	    self.cache.add(self,self.reloading)
	    self.incache = 1

    def reset(self,reload=0):
	# possible pathes through here:
	# if item gets created without api = disk_cache_access,
	#     then we get called with reload = 0
	# if item needs to be refreshed or is manually reloaded,
	#     then we get called with reload = 1
	if self.incache == 0: 
	    if self.stage != DONE:
		return
	    assert(self.api is None)
	self.api = protocols.protocol_access(self.url,
					     self.mode, self.params,
					     data=self.postdata)
	self.init_new_load(META)
	self.reloading = reload

    def init_new_load(self,stage):
	self.meta = None
	self.data = []
	self.datalen = 0
	self.datamap = {}
	self.stage = stage
	self.complete = 0

    def refresh(self,when):
	params = copy.copy(self.params)
	params['If-Modified-Since'] = when.get_str()
	api = protocols.protocol_access(self.url,
					self.mode, params,
					data=self.postdata)
	errcode, errmsg, headers = api.getmeta()
	### which errcode should I try to handle
	if errcode == 304:
	    # we win! it hasn't been modified
	    # but we probably need to delete the api object
	    api.close()
	    pass
	elif errcode == 200:
	    self.api = api
	    self.init_new_load(self.stage)
	    self.meta = (errcode, errmsg, headers)
	    self.reloading = 1
	else:
	    # there may be cases when we get an error response that
	    # doesn't require us to delete the object (a server busy
	    # response?). those are *not* handled.
	    self.api = api
	    self.init_new_load(self.stage)
	    self.meta = (errcode, errmsg, headers)
	    self.reloading = 1

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
	print "getdata(%5d,%5d)\tdatalen %5d" % (offset,maxbytes,self.datalen)
	while self.stage == DATA and offset >= self.datalen:
	    buf = self.api.getdata(maxbytes)
	    if not buf:
		self.finish()
		self.complete = 1
	    else:
		self.data.append(buf)
		self.datamap[offset] = len(self.data) - 1
		self.datalen = self.datalen + len(buf)

	try:
	    # the common case
	    chunk = self.data[self.datamap[offset]]
	    if len(chunk) > maxbytes:
		# you really don't want to do this
		return chunk[0:maxbytes]
	    else:
		return chunk
	except KeyError:
	    # the EOF marker isn't caught
	    if self.complete == 1 and offset >= self.datalen:
		return ''
	    ###
	    ### WARNING: this lookup is costly, please avoid
	    ###          cost is O(k), where k is # of chunks
	    ###          if you use this a lot, you'll get O(N^2) reads
	    ###
	    delta = offset + 1
	    chunk_key = None
	    for chunk_offset in self.datamap.keys():
		if offset > chunk_offset:
		    diff = offset - chunk_offset
		    if diff < delta:
			delta = diff
			chunk_key = chunk_offset
	    print self
	    print "\tfailed to find chunk for offset ", offset
	    print "\tcloset chunk starts at ", chunk_key
	    print self.datamap
	    chunk = self.data[self.datamap[chunk_key]]
	    return chunk[delta:]

    def fileno(self):
	if self.api:
	    return self.api.fileno()
	else:
	    return -1

    def abort(self):
	self.finish()

    def finish(self):
	if self.cache:
	    self.cache.deactivate(self.key)
	    if not (self.meta and self.meta[0] == 200):
		self.cache.delete(self.key)
	self.stage = DONE
	api = self.api
	self.api = None
	if api:
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

    def iscached(self):
	return self.item and self.item.iscached()

    def __repr__(self):
	return "CacheAPI(%s)" % self.item

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
	print "api:getdata(%5d,%5d) got %5d bytes" % (self.offset,maxbytes,len(data))
	if not data:
	    self.close()
	return data

    def fileno(self):
	if self.fno < 0:
	    self.fno = self.item.fileno()
	    if self.fno >= 0:
		self.fno = os.dup(self.fno)
	return self.fno

    def register_reader(self,reader):
	self.item.api.register_reader(reader)

    def tk_img_access(self):
	if hasattr(self.item.api, 'tk_img_access'):
	    return self.item.api.tk_img_access()
	else:
	    return None, None

    def close(self):
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
