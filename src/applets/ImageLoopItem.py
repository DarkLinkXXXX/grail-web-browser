# Java compatibility hack

from Tkinter import *
import urllib
import time

class ImageLoopItem:

    def __init__(self, master, img='doc:/demo/images/duke/',
		 pause=3900, align=None, **kw):
	self.master = master
	self.pause = pause
	self.browser = master.grail_browser
	self.images = []
	i = 0
	if img and img[-1] != '/': img.append('/')
	while 1:
	    i = i+1
	    url = "%sT%s.gif" % (img, i)
	    image = self.browser.get_image(url)
	    if not image: break
	    self.images.append(image)
	self.label = Label(master, text=url)
	self.label.pack()
	self.index = 0
	if self.images:
	    self.update()

    def update(self):
	if self.index >= len(self.images):
	    delay = 100 + self.pause
	    self.index = 0
	else:
	    delay = 100
	try:
	    self.label['image'] = self.images[self.index]
	    self.index = self.index + 1
	    self.master.tk.createtimerhandler(delay, self.update)
	except:
	    pass
