from Tkinter import *

class ImageWindow(Frame):

    def __init__(self, viewer, url, src, alt, usemap, ismap, align,
		 width, height, borderwidth):  
	self.viewer = viewer
	self.context = self.viewer.context
	self.src, self.alt, self.align = src, alt, align
	### set up mapping is either and server map or a client map
	if usemap:
	    self.map = usemap
	    self.url = None
	    self.ismap = None
	elif ismap:
	    self.ismap = 1
	    self.url = url
	    self.map = None
	else:
	    self.url = url
	    self.ismap = None
	    self.map = None
	bg = viewer.text['background']
	Frame.__init__(self, viewer.text, borderwidth=borderwidth,
		       background=bg)
	self.label = Label(self, text=self.alt, background=bg)
	self.label.pack(fill=BOTH, expand=1)
	self.image_loaded = 0
	if width > 0 and height > 0:
	    self.propagate(0)
	    self.config(width=width + 2*borderwidth,
			height=height + 2*borderwidth)
	if self.url:
	    self['background'] ='blue'	# XXX should use style sheet
	    self.bind('<Enter>', self.enter)
	    self.bind('<Leave>', self.leave)
	    if self.ismap:
		self.label.bind('<Motion>', self.motion)
	    self.label.bind('<ButtonRelease-1>', self.follow)
	else:
	    if self.map:
		self.bind('<Enter>', self.enter)
		self.bind('<Leave>', self.leave)
		self.label.bind('<Motion>', self.motion)
		self.label.bind('<ButtonRelease-1>', self.follow)
	    else:
##		self['background'] = 'black' # XXX for debug
		self.label.bind('<ButtonRelease-1>', self.toggle_loading_image)
	self.label.bind('<ButtonRelease-3>', self.toggle_loading_image)
	self.image = self.context.get_async_image(self.src)
	if self.image:
	    self.label['image'] = self.image

    def enter(self, event):
	url = self.whichurl(event)
	if url:
	    self.context.enter(url)

    def leave(self, event):
	self.context.leave()

    def motion(self, event):
	url = self.whichurl(event)
	if url:
	    self.context.enter(url)

    def follow(self, event):
	url = self.whichurl(event)
	if url:
	    self.context.follow(url)
	else:
	    self.context.leave()

    def whichurl(self, event):
	# perhaps having a usemap and an ismap is a bad idea
	# because we now need *two* tests for maps when the 
	# common case might be no map
	if self.ismap:
	    return self.url + "?%d,%d" % (event.x, event.y)
	elif self.map:
	    return self.map.url(event.x,event.y)
	return self.url

    def toggle_loading_image(self, event=None):
	if self.image:
	    if hasattr(self.image, 'get_load_status'):
		status = self.image.get_load_status()
		if status == 'loading':
		    self.image.stop_loading()
		else:
		    self.image.start_loading(reload=1)
	else:
	    print "[no image]"

