# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

import tempfile
import os
from Tkinter import *
from formatter import AS_IS

class parse_image_gif:

    """Parser for image/gif files.

    Collect all the data on a temp file and then create an in-line
    image from it.

    """

    def __init__(self, viewer, reload=0):
	self.tf = self.tfname = None
	self.viewer = viewer
	self.viewer.new_font((AS_IS, AS_IS, AS_IS, 1))
	self.tfname = tempfile.mktemp()
	self.tf = open(self.tfname, 'wb')
	self.label = Label(self.viewer.text, text=self.tfname,
			   highlightthickness=0, borderwidth=0)
	self.viewer.add_subwindow(self.label)

    def feed(self, data):
	self.tf.write(data)

    def close(self):
	if self.tf:
	    self.tf.close()
	    self.tf = None
	    self.label.image = PhotoImage(file=self.tfname)
	    self.label.config(image=self.label.image)
	if self.tfname:
	    try:
		os.unlink(self.tfname)
	    except os.error:
		pass
