from assert import assert

class ImageCache:
    
    """a cache for Tk image objects and their python wrappers

    The current goal of this cache is to provide a safe mechanism for
    sharing image objects between multiple Viewer windows.

    In future release, the image cache should actually delete objects
    from the cache (what a concept!). Currently, a Grail process will
    grow without bound as new images are displayed. This is a bug.
    """

    def __init__(self, url_cache):
	self.image_objects = {}
	self.old_objects = {}
	self.current_owners = {}
	self.url_cache = url_cache

    def debug_show_state(self):
	print "debugging ouput\ncurrent state of image cache"
	for image in self.image_objects.keys():
	    print "Image: %s. Owners=%s" % (image,
					    self.current_owners[image])
	for owner in self.old_objects.keys():
	    print "Old images owned by ", owner
	    for image in self.old_objects[owner]:
		print image

    def get_image(self, url):
	if url and self.image_objects.has_key(url):
	    self.url_cache.touch(url)
	    return self.image_objects[url]
	else:
	    return None

    def set_image(self, url, image, owner):
	if self.image_objects.has_key(url):
	    if owner not in self.current_owners[url] \
	       or len(self.current_owners[url]) > 1:
		for other_owner in self.current_owners[url]:
		    if other_owner != owner:
			self.keep_old_copy(other_owner, image)
		#self.debug_show_state()
	self.image_objects[url] = image
	self.current_owners[url] = [owner]

    def keep_old_copy(self, owner, image):
	if not self.old_objects.has_key(owner):
	    self.old_objects[owner] = []
	self.old_objects[owner].append(image)

    def owner_exiting(self, owner):
	del self.old_objects[owner]
