from Tkinter import *

class ImageWindow(Frame):

    def __init__(self, viewer, url,
		 src, alt, ismap, align, width, height, borderwidth):
	self.viewer = viewer
	self.url = url
	self.src, self.alt, self.ismap, self.align = src, alt, ismap, align
	self.browser = self.viewer.browser
	Frame.__init__(self, viewer.text, borderwidth=borderwidth)
	self.label = Label(self, text=self.alt)
	self.label.pack(fill=BOTH, expand=1)
	self.pack()
	self.image_loaded = 0
	if width > 0 and height > 0:
	    self.propagate(0)
	    self.config(width=width, height=height)
	if self.url:
	    self['background'] ='blue'	# XXX should use style sheet
	    self.bind('<Enter>', self.enter)
	    self.bind('<Leave>', self.leave)
	    self.label.bind('<ButtonRelease-1>', self.follow)
	else:
##	    self['background'] = 'black' # XXX for debug
	    self.label.bind('<ButtonRelease-1>', self.toggle_loading_image)
	self.label.bind('<ButtonRelease-3>', self.toggle_loading_image)
	self.image = self.browser.get_async_image(self.src)
	if self.image:
	    self.label['image'] = self.image

    def enter(self, event):
	self.browser.enter(self.url)

    def leave(self, event):
	self.browser.leave()

    def follow(self, event):
	self.browser.follow(self.url)

    def toggle_loading_image(self, event=None):
	if self.image:
	    if hasattr(self.image, 'get_load_status'):
		status = self.image.get_load_status()
		if status == 'loading':
		    self.image.stop_loading()
		else:
		    self.image.start_loading()
	else:
	    print "[no image]"
