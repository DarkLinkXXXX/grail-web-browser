from Cache import CacheItem, CacheAPI
from assert import assert
import urlparse
import string
import os
import time
import ht_time
import grailutil
import regex

META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages

CacheMiss = 'Cache Miss'
CacheEmpty = 'Cache Empty'
CacheReadFailed = 'Cache Item Expired or Missing'
CacheFileError = 'Cache File Error'

class CacheManager:
    """Manages one or more caches in hierarchy.

    The only methods that should be used by the application is
    open() and add_cache(). Other methods are intended for use by the
    cache itself.  

    overview of CacheManager and Cache organization

    CM has list of caches (could have more than one cache)
    
    items = {}: contains an entry for all the URLs in all the
    caches. value is a cache entry object (cf DiskCacheEntry
    below), has a get method that returns an protocol API object

    active = {}: contains an entry for each URL that is open in a
    browser window. this is the shared object list. if there is a
    request for an active page, a second CacheAPI for the same object
    is returned. the list stores CacheItems, which contain a reference
    count; when that cound reaches zero, it removes itself from the
    list. 

    freshness: CM is partly responsible for checking the freshness of
    pages. (pages with explicit TTL know when they expire.) freshness
    tests are preference driven, can be never, per session, or per
    time-unit. on each open, check to see if we should send an
    If-Mod-Since to the original server (based on fresh_p method).

    """
    
    def __init__(self, app):
	"""Initializes cache manager, creates disk cache.

	Basic disk cache characteristics loaded from 	"""
	
	self.app = app
	self.caches = []
	self.items = {}
	self.active = {}
	self.disk = None
	self.disk = DiskCache(self, self.app.prefs.GetInt('disk-cache',
						     'size') * 1024,
			 self.app.prefs.Get('disk-cache', 'directory'))
	self.set_freshness_test()
	self.app.prefs.AddGroupCallback('disk-cache', self.update_prefs)

    def update_prefs(self):
	self.set_freshness_test()
	size = self.caches[0].size = self.app.prefs.GetInt('disk-cache',
							   'size') \
							   * 1024
	new_dir = self.app.prefs.Get('disk-cache', 'directory')
	if new_dir != self.disk.directory:
	    self.disk.close()
	    self.disk = DiskCache(self, size, new_dir)

    def set_freshness_test(self):
	# read preferences to determine when pages should be checked
	# for freshness -- once per session, every n secs, or never
	fresh_type = self.app.prefs.Get('disk-cache', 'freshness-test-type')
	fresh_rate = int(self.app.prefs.GetFloat('disk-cache', 
					     'freshness-test-period') * 3600.0)

	if fresh_type == 'per session':
	    self.fresh_p = lambda key, self=self: \
			   self.fresh_every_session(self.items[key])
	    self.session_freshen = []
	elif fresh_type == 'periodic':
	    self.fresh_p = lambda key, self=self, t=fresh_rate: \
			   self.fresh_periodic(self.items[key],t)  
	elif fresh_type == 'never':
	    self.fresh_p = lambda x: 1
	else: #         == 'always'
	    self.fresh_p = lambda x: 0

    def open(self, url, mode, params, reload=0, data=None):
	"""Opens a URL and returns a protocol API for it.

	This is the method called by the Application to load a
	URL. First, it checks the shared object list (and returns a
	second reference to a URL that is currently active). Then it
	calls open routines specialized for GET or POST.
	"""

	key = self.url2key(url, mode, params)
	if mode == 'GET':
	    if self.active.has_key(key):
		if reload:
		    self.active[key].reset()
		return CacheAPI(self.active[key])
	    return self.open_get(key, url, mode, params, reload, data)
	elif mode == 'POST':
	    return self.open_post(key, url, mode, params, reload, data)

    def open_get(self, key, url, mode, params, reload, data):
	"""open() method specialized for GET request.

	Performs several steps:
	1. Check for the URL in the cache.
	2. If it is in the cache,
	      1. Create a CacheItem for it.
	      2. Reload the cached copy if reload flag is on.
	      3. Refresh the page if the freshness test fails.
	   If it isn't in the cache,
	      1. Create a CacheItem (which will create a CacheEntry 
   	      after the page has been loaded.)
	3. call activate(), which adds the URL to the shared object
	list and creates a CacheAPI for the item
	"""
	try:
	    api = self.cache_read(key)
	except CacheReadFailed, cache:
	    cache.evict(key)
	    api = None
	if api:
	    # creating reference to cached item
	    item = CacheItem(url, mode, params, self, key, data, api)
	    if reload:
		item.reset(reload)
		self.touch(key)
	    elif not self.fresh_p(key):
		# is this direct reference to the headers dangerous?
		item.refresh(self.items[key].lastmod)
		self.touch(key,refresh=1)
	else:
	    # cause item to be loaded (and perhaps cached)
	    item = CacheItem(url, mode, params, self, key, data)
	return self.activate(item)

    def open_post(self, key, url, mode, params, reload, data):
	"""Open a URL with a POST request. Do not cache."""
	key = self.url2key(url, mode, params)
	return self.activate(CacheItem(url, mode, params, None, key,
				       data))

    def activate(self,item):
	"""Adds a CacheItem to the shared object list and returns CacheAPI.
	"""
	self.active[item.key] = item
	return CacheAPI(self.active[item.key])

    def deactivate(self,key):
	"""Removes a CacheItem from the shared object list."""
	if self.active.has_key(key):
	    del self.active[key]

    def add_cache(self, cache):
	"""Called by cache to notify manager this it is ready."""
	self.caches.append(cache)

    def close_cache(self, cache):
	self.caches.remove(cache)

    def cache_read(self,key):
	"""Checks cache for URL. Returns protocol API on hit.

	Looks for a cache entry object in the items dictionary. If the
	CE object is found, call its method get() to create a protocol
	API for the item.
	"""
	if self.items.has_key(key):
	    return self.items[key].get()
	else:
	    return None

    def touch(self,key=None,url=None,refresh=0):
	"""Calls touch() method of CacheEntry object."""
	if url:
	    key = self.url2key(url,'GET',{})
	if key and self.items.has_key(key):
	    self.items[key].touch(refresh)

    def expire(self,key):
	"""Should not be used."""
	assert('night' == 'day')
	assert(self.items.has_key(key))
	self.items[key].evict()

    def delete(self, keys, evict=1):
	if type(keys) != type([]):
	    keys = [keys]

	if evict:
	    for key in keys:
		try:
		    self.items[key].cache.evict(key)
		except KeyError:
		    pass
	else:
	    for key in keys:
		try: 
		    del self.items[key]
		except KeyError:
		    pass

    def add(self,item,reload=0):
	"""If item is not in the cache and is allowed to be cached, add it. 
	"""
	try:
	    if not self.items.has_key(item.key) and self.okay_to_cache_p(item):
		self.caches[0].add(item)
	    elif reload == 1:
		self.caches[0].update(item)
	except CacheFileError, err_tuple:
	    (file, err) = err_tuple
	    print "error adding item %s (file %s): %s" % (item.url,
							  file, err)

    # list of protocols that we can cache
    cache_protocols = ['http', 'ftp', 'hdl']

    def okay_to_cache_p(self,item):
	"""Check if this item should be cached.

	This routine probably (definitely) needs more thought.
	Currently, we do not cache URLs with the following properties:
	1. The scheme is not on the list of cacheable schemes.
	2. The item is bigger than a quarter of the cache size.
	3. The 'Pragma: no-cache' header was sent
	4. The 'Expires: 0' header was sent
	5. The URL includes a query part '?'
	
	"""

	if len(self.caches) < 1:
	    return 0

	(scheme, netloc, path, parm, query, frag) = \
		 urlparse.urlparse(item.url)

	if not scheme in self.cache_protocols:
	    return 0

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

	if params.has_key('expires'):
	    expires = params['expires']
	    if expires == 0:
		return 0

	# dont' cache a query
	if query != '':
	    return 0

	return 1

    def fresh_every_session(self,entry):
	"""Refresh the page once per session"""
	if not entry.key in self.session_freshen:
	    self.session_freshen.append(entry.key)
	    return 0
	return 1

    def fresh_periodic(self,entry,max_age):
	"""Refresh it max_age seconds have passed since it was loaded."""
	try:
	    age = time.time() - entry.date.get_secs()
	    if age > max_age:
		return 0
	    return 1
	except AttributeError:
	    # if you don't tell me the date, I don't tell you it's stale
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

	OpenMarket sends two headers:
        Set-Cookie: OpenMarketSI=/@@THWJ@sL5SwMAQJOt; path=/;
        Location: http://pathfinder.com/@@THWJ@sL5SwMAQJOt/welcome/
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
    in a cache item, you must call fill() to create a new item. 

    The DiskCacheEntry object is shared by the DiskCache and the
    CacheManager. The method get() is called by the
    CacheManager and change the state of the DiskCache.

    The data members include:
    date -- the date of the most recent HTTP request to the server
    (either a regular load or an If-Modified-Since request)
    """

    def __init__(self, cache=None):
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

    string_date = regex.compile('^[A-Za-z]')

    def __repr__(self):
	return self.unparse()

    def parse(self,parsed_rep):
        """Reads transaction log entry.
         """
 	vars = string.splitfields(parsed_rep,'\t')
        self.key = vars[0]
        self.url = vars[1]
	self.file = vars[2]
        self.size = string.atoi(vars[3])
        self.type = vars[7]
	self.date = None
	self.lastmod = None
	self.expires = None
	for tup in [(vars[4], 'date'), (vars[5], 'lastmod'),
		     (vars[6], 'expires')]:
	    self.parse_assign(tup[0],tup[1])
	
    def parse_assign(self,rep,var):
	if rep == 'None':
	    setattr(self,var,None)
	elif self.string_date.match(rep) == 1:
	    setattr(self,var,HTTime(str=rep))
	else:
	    setattr(self,var,HTTime(secs=string.atof(rep)))
 
    def unparse(self):
        """Return entry for transaction log.
        """
	if not hasattr(self, 'file'):
	    self.file = ''
	string = reduce(lambda x,y: str(x) + '\t' + str(y), \
		 [self.key, self.url, self.file, self.size,
		  self.date, self.lastmod, self.expires, self.type])
	return string

    def get(self):
	"""Create a disk_cache_access API object and return it.

	Calls cache.get() to update the LRU information.

	Also checks to see if a page with an explicit Expire date has
	expired; raises a CacheItemExpired if it has.
	"""
	if self.expires:
	    if self.expires and self.expires.get_secs() < time.time():
		# we need to refresh the page; can we just reload?
		raise CacheReadFailed, self.cache
	self.cache.get(self.key) 
	try:
	    api = disk_cache_access(self.cache.get_file_path(self.file),
				    self.type, self.date, self.size)
	except IOError:
	    raise CacheReadFailed, self.cache
	return api

    def touch(self,refresh=0):
	"""Change the date of most recent check with server."""
	self.date = HTTime(secs=time.time())
	if refresh:
	    self.cache.log_entry(self)

    def delete(self):
	pass

def compare_expire_items(item1,item2):
    """used with list.sort() to sort list of CacheEntries by expiry date."""
    e1 = item1.expires.get_secs() 
    e2 = item2.expires.get_secs()
    if e1 > e2:
	return 1
    elif e2 > e1:
	return -1
    else:
	return 0
    
class DiskCache:
    """Persistent object cache.

    need to discuss:

    use_order

    the log: writes every change to cache or use_order, writes
    flushed, do a checkpoint run on startup, format is tuple (entry
    type, object), where entry type is add, evict, update use_order,
    version. 

    expires

    evict

    Note: Nowhere do we verify that the disk has enough space for a
    full cache.

    """

    def __init__(self, manager, size, directory):
	self.max_size = size
	self.size = 0
	if hasattr(os.path, 'expanduser'):
		directory = os.path.expanduser(directory)
	if not os.path.isabs(directory):
		directory = os.path.join(grailutil.getgraildir(), directory)
	self.directory = directory
	self.manager = manager
	self.manager.add_cache(self)
	self.items = {}
	self.use_order = []
	self.log = None
	self.checkpoint = 0
	self.expires = []
	self.types = {}

	grailutil.establish_dir(self.directory)
	self._read_metadata()
	self._reinit_log()

	# check preferences
	bool = self.manager.app.prefs.GetInt('disk-cache', 'checkpoint')
	if bool:
	    self.manager.app.register_on_exit(lambda self=self: \
					      self._checkpoint_metadata())

    log_version = "1.2"

    def close(self):
	self._checkpoint_metadata()
	self.manager.delete(self.items.keys(), evict=0)
	del self.items
	del self.expires
	self.manager.close_cache(self)
	self.manager = None

    def _read_metadata(self):
	"""Read the transaction log from the cache directory.

	Reads the pickled log entries and re-creates the cache's
	current contents and use_order from the log.

	A version number is included, but currently we only assert
	that a the version number read is the same as the current
	version number.
	"""
	logpath = os.path.join(self.directory, 'LOG')
	try:
	    log = open(logpath)
	except IOError:
	    # now what happens if there is an error here?
	    log = open(logpath, 'w')
	    log.close()
	    return

	for line in log.readlines():
	    try:
		kind = line[0:1]	
		if kind == '2': # use update
		    key = line[2:-1]
		    self.use_order.remove(key)
		    self.use_order.append(key)
		elif kind == '1': 	    # delete
		    key = line[2:-1]
		    if self.items.has_key(key):
			self.size = self.size - self.items[key].size
			del self.items[key]
			del self.manager.items[key]
			self.use_order.remove(key)
			assert(not key in self.use_order)
		elif kind == '0': # add
		    newentry = DiskCacheEntry(self)
		    newentry.parse(line[2:-1])
		    if not self.items.has_key(newentry.key):
			self.use_order.append(newentry.key)
		    newentry.cache = self
		    self.items[newentry.key] = newentry
		    self.manager.items[newentry.key] = newentry
		    self.size = self.size + newentry.size
		elif kind == '3': # version (hopefully first)
		    ver = line[2:-1]
		    if ver != self.log_version:
                   ### clear out anything we might have read
                   ### and bail. this is an old log file.
			if len(self.use_order) > 0:
			    self.use_order = []
			    for key in self.items.keys():
				del self.items[key]
				del self.manager.items[key]
				self.size = 0
			    return
		    assert(ver == self.log_version)
	    except IndexError:
		# ignore this line
		pass

    def _checkpoint_metadata(self):
	"""Checkpoint the transaction log.

	Creates a new log that contains only the current state of the
	cache.
	"""
	if self.log:
	    self.log.close()
	try:
	    newpath = os.path.join(self.directory, 'CHECKPOINT')
	    newlog = open(newpath, 'w')
	    newlog.write('3 ' + self.log_version + '\n')
	    for key in self.use_order:
		self.log_entry(self.items[key],alt_log=newlog)
	    newlog.close()
	    logpath = os.path.join(self.directory, 'LOG')
	    os.rename(newpath, logpath)
	except:
	    print "exception during checkpoint"

    def _reinit_log(self):
	"""Open the log for writing new transactions."""
	logpath = os.path.join(self.directory, 'LOG')
	self.log = open(logpath, 'a')

    def log_entry(self,entry,delete=0,alt_log=None):
	"""Write to the log adds and evictions."""
	if alt_log:
	    dest = alt_log
	else:
	    dest = self.log
	if delete:
	    dest.write('1 ' + entry.key + '\n')
	else:
	    dest.write('0 ' + entry.unparse() + '\n')
	dest.flush()

    def log_use_order(self,key):
	"""Write to the log changes in use_order."""
	if self.items.has_key(key):
	    self.log.write('2 ' + key + '\n')
	    # should we flush() here? probably...
	    self.log.flush()

    def erase_cache(self):
	
	def walk_erase(nil,dir,files):
	    for file in files:
		path = os.path.join(dir,file)
		if os.path.isfile(path):
		    os.unlink(path)
	
	os.path.walk(self.directory, walk_erase, None)

    def erase_unlogged_files(self):

	def walk_erase_unknown(known,dir,files):
	    for file in files:
		if not known.has_key(file):
		    path = os.path.join(dir,file)
		    if os.path.isfile(path):
			os.unlink(path)

	files = map(lambda entry:entry.file, self.items.values())
	file_dict = { 'LOG': 1 }
	for file in files:
	    file_dict[file] = 1
	os.path.walk(self.directory, walk_erase_unknown, file_dict)

    def get(self,key):
	"""Update and log use_order."""
	assert(self.items.has_key(key))
	self.use_order.remove(key)
	self.use_order.append(key)
	self.log_use_order(key)

    def update(self,object):
	# this is simple, but probably not that efficient
	self.evict(object.key)
	self.add(object)

    def add(self,object):
	"""Creates a DiskCacheEntry for object and adds it to cache.

	Examines the object and its headers for size, date, type,
	etc. The DiskCacheEntry is placed in the DiskCache and the
	CacheManager and the entry is logged.

	XXX Need to handle replacement better?
	"""
	respcode, msg, headers = object.meta
	size = len(object.data)

	self.make_space(size)

	newitem = DiskCacheEntry(self)
	(date, lastmod, expires, ctype) = self.read_headers(headers)
	newitem.fill(object.key, object.url, size, date, lastmod,
		   expires, ctype)
	newitem.file = self.get_file_name(newitem)
	if expires:
	    self.add_expireable(newitem)

	self.make_file(newitem,object)
	self.log_entry(newitem)

	self.items[object.key] = newitem
	self.manager.items[object.key] = newitem
	self.use_order.append(object.key)

	return newitem

    def read_headers(self,headers):
	if headers.has_key('date'):
	    date = headers['date']
	else:
	    date = time.time()

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
	    # what is the proper default content type?
	    ctype = 'text/html'

	return (date, lastmod, expires, ctype)


    def add_expireable(self,entry):
	"""Adds entry to list of pages with explicit expire date."""
	self.expires.append(entry)

    def get_file_name(self,entry):
	"""Invent a filename for a new cache entry."""
	filename = 'spam' + str(time.time()) + self.get_suffix(entry.type)
	return filename

    def get_file_path(self,filename):
	path = os.path.join(self.directory, filename)
	return path

    def get_suffix(self,type):
	if self.types.has_key(type):
	    return self.types[type]
	else:
	    for suf, stype in self.manager.app.suffixes_map.items():
		if type == stype:
		    self.types[type] = suf
		    return suf
	return ''

    def make_file(self,entry,object):
	"""Write the object's data to disk."""
	path = self.get_file_path(entry.file)
	try:
	    f = open(path, 'w')
	    f.write(object.data)
	    f.close()
	except IOError, err:
	    raise CacheFileError, (path, err)

    def make_space(self,amount):
	"""Ensures that there are amount bytes free in the disk cache.

	If the cache does not have amount bytes free, pages are
	evicted. First, we check the list of pages with explicit
	expire dates and evict any that have expired. If we need more
	space, evict the least recently used page. Continue LRU
	eviction until enough space is available.

	Raises CacheEmpty if there are no entries in the cache, but
	amount bytes are not available.
	"""

	if self.size + amount > self.max_size:
	    self.evict_expired_pages()

	try:
	    while self.size + amount > self.max_size:
		self.evict_any_page()
	except CacheEmpty:
	    print "Can't make more room in the cache"
	    pass
	    # this is not the right thing to do, probably
	    # but I don't think this should ever happen
	self.size = self.size + amount

    def evict_any_page(self):
	"""Evict the least recently used page."""
	# get ride of least-recently used thing
	if len(self.items) > 0:
	    key = self.use_order[0]
	    self.evict(key)
	else:
	    raise CacheEmpty

    def evict_expired_pages(self):
	"""Evict any pages on the expires list that have expired."""
	self.expires.sort(compare_expire_items)
	size = len(self.expires)
	if size > 0 \
	   and self.expires[0].expires.get_secs() < time.time():
	    index = 0
	    t = time.time()
	    while index < size and self.expires[index].expires.get_secs() < t:
		index = index + 1
	    for item in self.expires[0:index]:
		self.evict(item.key)
	    del self.expires[0:index]

    def evict(self,key):
	"""Remove an entry from the cache and delete the file from disk."""
	self.use_order.remove(key)
	evictee = self.items[key]
	del self.manager.items[key]
	del self.items[key]
	if key in self.expires:
	    self.expires.remove(key)
	try:
	    os.unlink(self.get_file_path(evictee.file))
	except (os.error, IOError), err:
	    # print "error deleteing %s from cache: %s" % (key, err)
	    pass
	self.log_entry(evictee,1) # 1 indicates delete entry
	evictee.delete()
	self.size = self.size - evictee.size

class disk_cache_access:
    """protocol access interface for disk cache"""

    def __init__(self, filename, content_type, date, len):
	self.headers = { 'content-type' : content_type,
			 'date' : date,
			 'content-length' : str(len) }
	self.filename = filename
	try:
	    self.fp = open(filename)
	except IOError, err:
	    print "io error opening %s: %s" % (filename, err)
	    # propogate error through
	    raise IOError, err
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

    def tk_img_access(self):
	"""Return the cached filename and content-type.

	Used by AsyncImage to create Tk image objects directly from
	the file in the disk cache.
	"""
	return self.filename, self.headers['content-type']

class HTTime:
    """Stores time as HTTP string or seconds since epoch or both.

    Lazy conversions from one format to the other.
    """
    # HTTP defines three date formats, but only one is supposed to be
    # produced by an HTTP application. (The other two you're supposed to
    # handle for backwards compatibility.) It would be nice to accept
    # the two old date formats as str input and convert them to the
    # preferred format.

    def __init__(self,any=None,str=None,secs=None):
	if any:
	    if type(any) == type(''):
		str = any
	    elif type(any) in [type(1), type(.1)]:
		secs = any
	if str and str != '':
	    self.str = str
	else:
	    self.str = None
	if secs:
	    self.secs = secs
	else:
	    self.secs = None

    def get_secs(self):
	if not self.secs:
	    try:
		self.secs = ht_time.parse(self.str)
	    except:
		# if there is a parsing error, we bail
		self.secs = 0
	return self.secs

    def get_str(self):
	if not self.str:
	    self.str = ht_time.unparse(self.secs)
	return self.str
    
    def __repr__(self):
	if self.secs:
	    return str(self.secs)
	elif self.str:
	    return self.str
	else:
	    return str(None)
