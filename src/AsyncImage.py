from FileReader import FileReader, TempFileReader
from Tkinter import *


class ImageTempFileReader(TempFileReader):

    def __init__(self, browser, api, image):
	self.image = image
	self.image.reader = self
	TempFileReader.__init__(self, browser, api)

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

    def __init__(self, browser, url, **kw):
	apply(PhotoImage.__init__, (self,), kw)
	self.browser = browser
	self.url = url
	self.reader = None
	self.loaded = 0

    def load_synchronously(self, browser=None):
	if not self.loaded:
	    self.start_loading(browser)
	    if self.reader:
		self.reader.geteverything()
	return self.loaded

    def start_loading(self, browser=None):
	if browser: self.browser = browser
	if self.reader:
	    return
	self['file'] = makestopsign()
	api = self.browser.app.open_url(self.url, 'GET', {},
					self.loaded) # Through cache
	ImageTempFileReader(self.browser, api, self)

    def stop_loading(self):
	if not self.reader:
	    return
	self.reader.kill()
	self.blank()

    def set_file(self, filename):
	try:
	    self['file'] = filename
	except TclError:
	    self.blank()
	    print "*** bad image type:", self.url
	else:
	    self.loaded = 1

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


# XXX This leaves a temp file each run!

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
	_stopsign = _makestopsign()
    return _stopsign

def _makestopsign():
    import tempfile
    tfn = tempfile.mktemp()
    f = open(tfn, 'wb')
    f.write(STOPDATA)
    f.close()
    return tfn
