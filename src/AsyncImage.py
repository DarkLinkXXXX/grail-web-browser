from FileReader import TempFileReader
from Tkinter import *
import grailutil
import string

TkPhotoImage = PhotoImage

# Determine if the Python Imaging Library is available.
#
# Note that "import Image" is not sufficient to test the availability of
# the image loading capability.  Image can be imported without _imaging
# and still supports identification of file types.
#
try:
    import _imaging
except ImportError:
    use_pil = 0
    class PILPhotoImage:
	pass
else:
    import Image
    import ImageDraw
    import ImageTk
    ATTEMPT_TRANSPARENCY = 0
    PILPhotoImage = ImageTk.PhotoImage
    use_pil = 1


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
	    if self.image_filters.has_key(ctype) and not use_pil:
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
	'image/png':
	    # This requires pngtopnm which isn't standard netpbm yet
	    'pngtopnm | ppmtogif -transparent "#FFFFFF" 2>/dev/null',
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




class BaseAsyncImage:

    def setup(self, context, url, reload):
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
	self.do_color_magic()
	try:
	    self['file'] = filename
	except TclError:
	    self.show_bad()
	else:
	    self.loaded = 1

    def do_color_magic(self):
	self.context.root.tk.setvar("TRANSPARENT_GIF_COLOR",
				    self.context.viewer.text["background"])

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


class TkAsyncImage(BaseAsyncImage, TkPhotoImage):

    def __init__(self, context, url, reload=0, width=None, height=None, **kw):
	apply(TkPhotoImage.__init__, (self,), kw)
	self.setup(context, url, reload)

    def get_cache_key(self):
	return self.url, 0, 0


class PILAsyncImage(BaseAsyncImage, PILPhotoImage):

    __width = 0
    __height = 0

    def __init__(self, context, url, reload=0, width=None, height=None, **kw):
	#
	# Fake out the ImageTk.PhotoImage.__init__() since we don't have
	# the needed info yet:
	#
	self.setup(context, url, reload)
	self.image = TkPhotoImage()
	self._PhotoImage__tk = self.image
	# Make sure these are integers >= 0
	if width and height:
	    self.__width = width
	    self.__height = height

    def blank(self):
	self.image.blank()

    def get_cache_key(self):
	# Note that two different cache keys may be generated for an image
	# depending on how they are specified.  In particular, the keys
	# (URL, 0, 0) and (URL, WIDTH, HEIGHT) may be generated for the same
	# real image (not Image object) if WIDTH and HEIGHT are the default
	# dimensions of the image and the image is specified both with and
	# without size hints.  This still generates no more than two distinct
	# keys for otherwise identical image objects.
	#
	return self.url, self.__width, self.__height

    def set_file(self, filename):
	try:
	    im = Image.open(filename)
	    im.load()			# force loading to catch IOError
	except (IOError, ValueError):
	    # either of these may occur during decoding...
	    return self.show_bad()
	format = im.format
	real_mode = im.mode
	real_size = im.size
	# this transparency stuff should be greatly simplified on the next
	# release of PIL....
	# handle transparent GIFs:
	if im.format == "GIF" \
	   and im.info["version"] != "GIF87a" \
	   and im.info.has_key("background") \
	   and ATTEMPT_TRANSPARENCY:
	    r, g, b = self.context.viewer.text.winfo_rgb(
		self.context.viewer.text["background"])
	    r = r / 255			# convert these to 8-bit versions
	    g = g / 255
	    b = b / 255
	    im = transp_gif_to_rgb(im, (r, g, b))
	#
	if self.__width:
	    w, h = im.size
	    if w != self.__width or h != self.__height:
		im = im.resize((self.__width, self.__height))
	mode = real_mode = im.mode
	if mode not in ('1', 'L'):
	    mode = 'RGB'
	self._PhotoImage__mode = mode
	self._PhotoImage__size = im.size
	self.do_color_magic()
	self.paste(im)
	w, h = im.size
	self.image['width'] = w
	self.image['height'] = h

    def width(self):
	return self.__width

    def height(self):
	return self.__height

    def __setitem__(self, key, value):
	if key == "file":
	    self.do_color_magic()
	self.image[key] = value


def transp_gif_to_rgb(im, (r, g, b)):
    """Translate a P-mode GIF with transparency to an RGB image. 

    im
	The GIF image.

    (r, g, b)
	The RGB-value to use for the transparent areas.  These should be
	8 bits for each band.
    """
    # This is really quite slow.
    bg = im.info["background"]
    # Maybe we can use a palette manipulation?
##     print "========"
##     print im.palette
##     xxx, pal = im.palette
##     newcol = chr(r) + chr(g) + chr(b)
##     pal = pal[: bg*3] + newcol + pal[bg*3 + 3 :]
##     print (xxx, pal)
##     im.palatte = (xxx, pal)
##     print im.palette
##     return im.convert("RGB")
    #
    rgbimg = Image.new("RGB", im.size, (r<<24 | g <<16 | b<<8))
    mask = Image.new("1", im.size)
    drawing = ImageDraw.ImageDraw(mask)
    getpixel = im.getpixel
    point = drawing.point
    yrange = range(im.size[1])
    ylength = im.size[1]
    for x in range(im.size[0]):
	for pos in map(None, [x]*ylength, yrange):
	    if getpixel(pos) != bg:
		point(pos)
    rgbimg.paste(im, None, mask)
    return rgbimg


AsyncImage = TkAsyncImage
if use_pil:
    def AsyncImage(context, url, reload=0, **kw):
	global AsyncImage
	if context.app.prefs.GetBoolean("browser", "enable-pil"):
	    AsyncImage = PILAsyncImage
	else:
	    AsyncImage = TkAsyncImage
	return apply(AsyncImage, (context, url, reload), kw)
