from FileReader import TempFileReader
from Tkinter import *
import grailutil
import string

class ImageTempFileReader(TempFileReader):

    def __init__(self, context, api, image):
	self.image = image
	self.url = self.image.url
	TempFileReader.__init__(self, context, api)

    def handle_meta(self, errcode, errmsg, headers):
	TempFileReader.handle_meta(self, errcode, errmsg, headers)
	if errcode == 200:
	    try:
		ctype = headers['content-type']
	    except KeyError:
		return # Hope for the best
	    if self.image_filters.has_key(ctype):
		self.set_pipeline(self.image_filters[ctype])

    # List of image type filters
    image_filters = {
	'image/gif': '',
	'image/jpeg': 'djpeg -gif',
	'image/x-xbitmap':
	    'xbmtopbm | ppmtogif -transparent "#FFFFFF" 2>/dev/null',
	'image/tiff':
	    """(T=${TMPDIR-/usr/tmp}/@$$.tiff; cat >$T;
	        tifftopnm $T 2>/dev/null; rm -f $T)""",
	}

    def handle_done(self):
        self.image.set_file(self.getfilename())
	self.cleanup()

    def handle_error(self, errcode, errmsg, headers):
	if errcode == 401:
	    if headers.has_key('www-authenticate'):
		cred_headers = {}
		for k in headers.keys():
		    cred_headers[string.lower(k)] = headers[k]
		cred_headers['request-uri'] = self.image.url
		self.stop()
		credentials = self.image.context.app.auth.request_credentials(cred_headers)
		if credentials.has_key('Authorization'):
		    for k,v in credentials.items():
			self.image.headers[k] = v
		    # self.image.restart(self.image.url)
		    self.image.start_loading(self.image.context)
	self.image.set_error(errcode, errmsg, headers)
	self.cleanup()

    def stop(self):
	TempFileReader.stop(self)
	if self.image:
	    self.image.reader = None

    def cleanup(self):
	self.image = None
	import os
	try:
	    os.unlink(self.getfilename())
	except os.error:
	    pass


class AsyncImage(PhotoImage):

    def __init__(self, context, url, reload=0, **kw):
	apply(PhotoImage.__init__, (self,), kw)
	self.context = context
	self.url = url
	self.reader = None
	self.loaded = 0
	self.headers = {}
	if reload:
	    self.reload = 1
	else:
	    self.reload = 0

    def load_synchronously(self, context=None):
	if not self.loaded:
	    self.start_loading(context)
	    if self.reader:
		self.reader.geteverything()
	return self.loaded

    def start_loading(self, context=None, reload=0):
	# seems that the reload=1 when you click on an image that
	# you had stopped loading
	if context: self.context = context
	if self.reader:
	    return
	try:
	    api = self.context.app.open_url(self.url, 'GET', self.headers,
					    self.reload or reload) 
	except IOError, msg:
	    self.show_bad()
	    return
	self.show_busy()
	cached_file, content_type = api.tk_img_access()
	if cached_file \
	   and ImageTempFileReader.image_filters.has_key(content_type) \
	   and ImageTempFileReader.image_filters[content_type] == '':
	    api.close()
	    self.set_file(cached_file)
	else:
	    # even if the item is in the cache, use the ImageTempFile
	    # to handle the proper type coercion
	    self.reader = ImageTempFileReader(self.context, api, self)

    def stop_loading(self):
	if not self.reader:
	    return
	self.reader.kill()
	self.show_bad()

    def set_file(self, filename):
	self.context.root.tk.setvar("TRANSPARENT_GIF_COLOR",
				    self.context.viewer.text["background"])
	try:
	    self['file'] = filename
	except TclError:
	    self.show_bad()
	else:
	    self.loaded = 1

    def set_error(self, errcode, errmsg, headers):
	self.loaded = 0
	if errcode in (301, 302) and headers.has_key('location'):
	    self.url = headers['location']
	    self.start_loading()

    def is_reloading(self):
	return self.reload and not self.loaded

    def get_load_status(self):
	if self.reader:
	    return 'loading'
	else:
	    return 'idle'

    def show_bad(self):
	try:
	    self['file'] = grailutil.which("icons/sadsmiley.gif") or ""
	except TclError:
	    self.blank()

    def show_busy(self):
	try:
	    self['file'] = grailutil.which("icons/image.gif") or ""
	except TclError:
	    self.blank()
