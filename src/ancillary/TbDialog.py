# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:cnri/19980302135001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.4/", or file "LICENSE".

"""Modeless dialog displaying exception and traceback."""

from Tkinter import *
import tktools
import traceback

class TracebackDialog:

    def __init__(self, master, exc, val, tb):
	self.master = master
	self.exc = exc
	self.val = val
	self.tb = tb
	self.root = tktools.make_toplevel(self.master,
					  title="Traceback Dialog")
	self.close_button = Button(self.root,
				   text="Close",
				   command=self.close_command)
	self.close_button.pack(side=BOTTOM, pady='1m')
	self.label = Label(self.root, text="%s: %s" % (exc, str(val)))
	self.label.pack(fill=X)
	self.text, self.text_frame = tktools.make_text_box(self.root,
							   width=90)
	lines = traceback.format_exception(exc, val, tb)
	for line in lines:
	    self.text.insert(END, line + '\n')
	self.text.yview_pickplace(END)
	self.text["state"] = DISABLED

    def close_command(self):
	self.root.destroy()
