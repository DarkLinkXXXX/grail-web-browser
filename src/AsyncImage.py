from FileReader import TempFileReader
from Tkinter import *


class ImageTempFileReader(TempFileReader):

    def __init__(self, context, api, image):
	self.image = image
	self.image.reader = self
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
	if reload:
	    self.reload = 1
	else:
	    self.reload = 0

    direct_load = ['image/gif']

    def load_synchronously(self, context=None):
	if not self.loaded:
	    self.start_loading(context)
	    if self.reader:
		self.reader.geteverything()
	return self.loaded

    def start_loading(self, context=None):
	if context: self.context = context
	if self.reader:
	    return
	try:
	    self['file'] = makestopsign()
	except TclError:
	    pass
	try:
	    api = self.context.app.open_url(self.url, 'GET', {},
					    self.reload) # Through cache
	except IOError, msg:
	    self.blank()
	    return
	cached_file, content_type = api.tk_img_access()
	if cached_file and content_type in self.direct_load:
	    api.close()
	    self.set_file(cached_file)
	else:
	    # even if the item is in the cache, use the ImageTempFile
	    # to handle the proper type coercion
	    ImageTempFileReader(self.context, api, self)

    def stop_loading(self):
	if not self.reader:
	    return
	self.reader.kill()
	self.blank()

    def set_file(self, filename):
	self.context.root.tk.setvar("TRANSPARENT_GIF_COLOR",
				    self.context.viewer.text["background"])
	try:
	    self['file'] = filename
	except TclError:
	    self.blank()
	    print "*** bad image type:", self.url
	else:
	    self.loaded = 1
	self.context.root.update_idletasks()

    def set_error(self, errcode, errmsg, headers):
	self.blank()
	self.loaded = 0
	if errcode in (301, 302) and headers.has_key('location'):
	    self.url = headers['location']
	    self.start_loading()

    def get_load_status(self):
	if self.reader:
	    return 'loading'
	else:
	    return 'idle'


STOPDATA = """GIF87a \000 \000\360\000\000\377\377\377\000\000\000,\
\000\000\000\000 \000 \000\000\002z\204o\241\313\035\010#ptI\251\356\
\315:\275\016q\333\007bdx\226\210x\260\252\271\246/\352\315*c\227\370\
TY|\314\331\365|,a#R\374\004\225\024\344iY\3439\234\261\350rJk1\255\307\
\237\266\3525B\277\344+3\031\345\246\245\317m\331\355A{\325s6X>\216w\
\327\353$\226_\207\'\223\0238\230\343Rg\203\010\370\262H\326h\010\006\
\0119\264CY\351X\000\000;"""

_stopsign = None
def makestopsign():
    global _stopsign
    if not _stopsign:
	import sys
	if not hasattr(sys, 'exitfunc'): sys.exitfunc = None
	sys.exitfunc = lambda chain=sys.exitfunc: _cleanup(chain)
	_stopsign = _makestopsign()
    return _stopsign

def _makestopsign():
    import tempfile
    tfn = tempfile.mktemp()
    try:
	f = open(tfn, 'wb')
	f.write(STOPDATA)
	f.close()
    except IOError:
	print "Error creating temporary file! ",
	print "Make sure", tempfile.gettempdir(), "is writable."
	return ""
    return tfn

def _cleanup(chain=None):
    global _stopsign
    if _stopsign:
	import os
	tfn = _stopsign
	_stopsign = None
	try:
	    os.unlink(tfn)
	except os.error:
	    pass
    if chain:
	chain()
