"""Jeremy's cache classes.

"""

# need these?
META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages

from Cache import CacheItem, CacheAPI
from assert import assert
import urlparse
import string
import regsub
import os
import protocols
import time
import ht_time
import grailutil

CacheMiss = 'Cache Miss'
CacheEmpty = 'Cache Empty'
CacheItemExpired = 'Cache Item Expired'

class CacheManager:
    """Manages one or more caches in hierarchy.

    The only methods that should be used by the application is
    open() and add_cache(). Other methods are intended for use by the
    cache itself.  
    """
    
    def __init__(self, app):
	"""Initializes cache manager, storing pointer to application.

	Currently creates the disk cache and hardcodes its maximum
	size and location. Those things shouldn't happen here.
	"""
	
	self.app = app
	self.caches = []
	self.items = {}
	disk = DiskCache(self, 1048576, self.app.graildir + '/cache')

	# read preferences to determine when pages should be checked
	# for freshness -- once per session, every n secs, or never
	fresh_type = 'periodic'
	fresh_rate = 14400
	if fresh_type == 'per session':
	    self.fresh_p = lambda key, self=self: \
			   self.fresh_every_session(self.items[key])
	elif fresh_type == 'periodic':
	    self.fresh_p = lambda key, self=self, t=fresh_rate: \
			   self.fresh_periodic(self.items[key],t)  
	elif fresh_type == 'never':
	    self.fresh_p = lambda x: 1

    def open(self, url, mode, params, reload=0, data=None):
	if mode == 'GET':
	    return self.open_get(url, mode, params, reload, data)
	elif mode == 'POST':
	    return self.open_post(url, mode, params, reload, data)

    def add_cache(self, cache):
	"""Called by cache to notify manager this it is ready."""
	self.caches.append(cache)

    def cache_read(self,key):
	if self.items.has_key(key):
	    return self.items[key].get()
	else:
	    return None

    def touch(self,key):
	if self.items.has_key(key):
	    self.items[key].touch()

    def open_get(self, url, mode, params, reload, data):
	key = self.url2key(url, mode, params)
	try:
	    api = self.cache_read(key)
	except CacheItemExpired, cache:
	    cache.evict(key)
	    api = None
	if api:
	    # creating reference to cached item
	    item = CacheItem(url, mode, params, self, key, data, api)
	    if reload:
		item.reset(reload)
		self.touch(key)
	    # problem: 
	    elif not self.fresh_p(key):
		# is this direct reference to the headers dangerous?
		item.refresh(self.items[key].lastmod)
		self.touch(key)
	else:
	    # cause item to be loaded (and perhaps cached)
	    item = CacheItem(url, mode, params, self, key, data)
#	return item
	return CacheAPI(item)


    def open_post(self, url, mode, params, reload, data):
	# for now, never cache a POST
	key = self.url2key(url, mode, params)
#	return CacheItem(url, mode, params, None, key, data)
	return CacheAPI(CacheItem(url, mode, params, None, key, data))

    def expire(self,key):
	if self.items.has_key(key):
	    self.items[key].evict()

    def delete(self, object):
	print "delete called on %s" % object

    def add(self,item,reload=0):
	if len(self.caches): # need to guarantee that this can't happen
	    if not self.items.has_key(item.key) and self.okay_to_cache_p(item):
		self.caches[0].add(item)
	    elif reload == 1:
		self.caches[0].add(item)

    def okay_to_cache_p(self,item):
	"""Check if this item should be cached.

	This routine probably (definitely) needs more thought.
	"""

	(scheme, netloc, path, parm, query, frag) = \
		 urlparse.urlparse(item.url)

	# don't cache logos
	if scheme == 'logo': 
	    # is there a better place for this, since it gets called
	    # so often?
	    return 0
	# or should we be cautious and not cache any scheme unless we
	# know it is okay to cache it?

	code, msg, params = item.meta

	# don't cache really big things
	#####
	##### limit is hardcoded, please fix
	#####
	if len(item.data) > self.caches[0].max_size / 4:
	    return 0

	# don't cache things that don't want to be cached
	if params.has_key('pragma'):
	    pragma = params['pragma']
	    if pragma == 'no-cache':
		return 0

	return 1

    def fresh_every_session(self,entry):
	return 1

    def fresh_periodic(self,entry,max_age):
	age = time.time() - entry.date.get_secs()
	if age > max_age:
	    return 0
	return 1

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

	XXX Idea

	Servers that use session ids make it hard to
	cache. OpenMarket, however, sends the session id in the
	headers, so that we could strip it out of the URL. :-)

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


class DiskCacheEntry:
    """Data about item stored in a disk cache.

    __init__ only store the cache this entry is in. To place real data
    r    in a cache item, you must call fill() to create a new item or call
    parse() to read an entry in the transaction log. This is done to
    simplify the interface for reading to and writing from the log.

    """

    def __init__(self, cache):
	self.cache = cache

    def fill(self,key,url,size,date,lastmod,expires,ctype):
	self.key = key
	self.url = url
	self.size = size
	if date:
	    self.date = HTTime(date)
	else:
	    self.date = None
	if lastmod:
	    self.lastmod = HTTime(lastmod)
	else:
	    self.lastmod = None
	if expires:
	    self.expires = HTTime(expires)
	else:
	    self.expires = None
	self.type = ctype

    def parse(self,line):
	"""Reads transaction log entry.

	Determines if log entry is for evicition or addition. Fills
	the object's instance variables  and returns a key.
	"""

	evicted_p, vars = eval(line[:-1])
	self.key = vars[0]
	self.url = vars[1]
	self.size = vars[2]
	if type(vars[3]) == type(''):
	    self.date = HTTime(str=vars[3])
	else:
	    self.date = HTTime(secs=vars[3])
	if type(vars[4]) == type(''):
	    self.lastmod = HTTime(str=vars[4])
	else:
	    self.lastmod = HTTime(secs=vars[4])
	if type(vars[5]) == type(''):
	    if vars[5] == '':
		self.expires = None
	    else:
		self.expires = HTTime(str=vars[5])
	elif type(vars[5]) == type(1):
	    self.expires = HTTime(secs=vars[5])
	else:
	    self.expires = None
	self.type = vars[6]
	
	return evicted_p

    def unparse(self,delete_p=0):
	"""Return entry for transaction log.

	Entry includes indication of whether this item is being
	deleted.
	"""
	string = repr((delete_p,[self.key,self.url,self.size,self.date,self.lastmod,self.expires,self.type]))
	string = string + '\n'
	return string

    def get(self):
	if self.expires:
	    if self.expires and self.expires.get_secs() < time.time():
		# we need to refresh the page; can we just reload?
		raise CacheItemExpired, self.cache
	self.cache.get(self.key) #update the replace queue
	api = disk_cache_access(self.cache.get_file_path(self.key),
				self.type, self.date)
	return api

    def touch(self):
	self.date = HTTime(secs=time.time())

    def delete(self):
	pass
    
class DiskCache:
    """Persistent object cache.

    """

    def __init__(self,manager,size,directory):
	self.max_size = size
	self.size = 0
	self.directory = directory
	self.manager = manager
	self.manager.add_cache(self)
	self.items = {}
	self.use_order = []
	self.log = None
	self.checkpoint = 0

	grailutil.establish_dir(self.directory)
	self._read_metadata()
	self._reinit_log()

    def _read_metadata(self):
	###
	### this trashes all the data about what is LRU
	###

	logpath = os.path.join(self.directory, 'LOG')
	try:
	    log = open(logpath)
	except IOError:
	    # if we can't open the LOG, assume an empty cache
	    # should probably set up thread to erase directory?
	    log = open(logpath, 'w')
	    log.close()
	    return
	for line in log.readlines():
	    entry = DiskCacheEntry(self)
	    evicted_p = entry.parse(line)
	    if evicted_p:
		if self.items.has_key(entry.key):
		    del self.items[entry.key]
		    del self.manager.items[entry.key]
		    self.use_order.remove(entry.key)
		    self.size = self.size - entry.size
		    assert(not entry.key in self.use_order)
	    else:
		if not self.items.has_key(entry.key):
		    self.use_order.append(entry.key)
		self.items[entry.key] = entry
		self.manager.items[entry.key] = entry
		self.size = self.size + entry.size
	self._checkpoint_metadata()

    def _checkpoint_metadata(self):
	if self.log:
	    self.log.close()
	newpath = os.path.join(self.directory, 'CHECKPOINT')
	newlog = open(newpath, 'w')
	for entry in self.items.keys():
	    newlog.write(self.items[entry].unparse())
	newlog.close()
	logpath = os.path.join(self.directory, 'LOG')
	os.rename(newpath, logpath)
	self._reinit_log()

    def _reinit_log(self):
	logpath = os.path.join(self.directory, 'LOG')
	self.log = open(logpath, 'a')

    def log_entry(self,entry,delete=0):
	self.log.write(entry.unparse(delete))
	self.log.flush()

    def get(self,key):
	if self.items.has_key(key):
	    self.use_order.remove(key)
	    self.use_order.append(key)
	    # should probably do more here...
	    #  check for freshness
	    #  promote to memory cache for example?
	else:
	    ### UNTRAPPED EXCEPTION
	    # this should only be called if the CacheManager
	    # knows that this Cache has the key
	    raise CacheMiss

    def add(self,object):
##	print "DiskCache.add(%s)" % (object.key)
	
	respcode, msg, headers = object.meta
	size = len(object.data)

	self.make_space(size)
	self.make_file(object)

	newitem = DiskCacheEntry(self)
	if headers.has_key('date'):
	    date = headers['date']
	else:
	    date = int(time.time())

	if headers.has_key('last-modified'):
	    lastmod = headers['last-modified']
	else:
	    lastmod = date

	if headers.has_key('expires'):
	    expires = headers['expires']
	else:
	    expires = None

	if headers.has_key('content-type'):
	    ctype = headers['content-type']
	else:
	    ctype = 'text/html'

	newitem.fill(object.key, object.url, size, date, lastmod,
		     expires, ctype)

	self.log_entry(newitem)

	self.items[object.key] = newitem
	self.manager.items[object.key] = newitem
	self.use_order.append(object.key)

	return newitem

    def get_file_path(self,key):
	filename = regsub.gsub(os.sep,'_',key)
	path = os.path.join(self.directory, filename)
	return path

    def make_file(self,object):
	path = self.get_file_path(object.key)
	f = open(path, 'w')
	f.write(object.data)
	f.close()

    def make_space(self,amount):
	# perhaps expire would be a good thing to call here
	# definitely don't want to evict live things when we
	# could evict stale things
	try:
	    while self.size + amount > self.max_size:
		self.evict_any_page()
	except CacheEmpty:
	    print "Can't make more room in the cache"
	    pass
	    # this is not the right thing to do, probably
	    # but I don't think this should ever happen
	self.size = self.size + amount

    def expire(self):
	# get rid of things known to be stale
	pass

    def evict_any_page(self):
	# get ride of least-recently used thing
	if len(self.items) > 0:
	    key = self.use_order[0]
	    self.evict(key)
	else:
	    raise CacheEmpty

    def evict(self,key):
##	print "evict(%s)" % (key)
	self.use_order.remove(key)
	evictee = self.items[key]
	del self.manager.items[key]
	del self.items[key]
	os.unlink(self.get_file_path(key))
	self.log_entry(evictee,1) # 1 indicates delete entry
	evictee.delete()
	self.size = self.size - evictee.size

class disk_cache_access:
    """protocol access interface for disk cache"""

    def __init__(self, filename, content_type, date):
	self.headers = { 'content-type' : content_type,
			 'date' : date }
	self.filename = filename
	self.fp = open(filename)
	self.stage = DATA

    def pollmeta(self):
	return "Ready", 1

    def getmeta(self):
	return 200, "OK", self.headers

    def polldata(self):
	return "Ready", 1

    def getdata(self,maxbytes):
	# get some data from the disk
	data = self.fp.read(maxbytes)
	if not data:
	    self.state = DONE
	return data

    def fileno(self):
	try:
	    return self.fp.fileno()
	except AttributeError:
	    return -1

    def close(self):
	fp = self.fp
	self.fp = None
	if fp:
	    fp.close()

class HTTime:
    """Stores time as HTTP string or seconds since epoch or both.

    Lazy conversions from one format to the other.
    """
    def __init__(self,any=None,str=None,secs=None):
	if any:
	    if type(any) == type(''):
		str = any
	    elif type(any) == type(1):
		secs = any
	if str and str != '':
	    self.str = str
	else:
	    self.str = None
	if secs:
	    self.secs = int(secs)
	else:
	    self.secs = None

    def get_secs(self):
	if not self.secs:
	    self.secs = ht_time.parse(self.str)
	return self.secs

    def get_str(self):
	if not self.str:
	    self.str = ht_time.unparse(self.secs)
	return self.str
    
    def __repr__(self):
	if self.secs:
	    return repr(self.secs)
	elif self.str:
	    return '\'' + self.str + '\''
	else:
	    return '\'\''
