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
	self.root = Toplevel(self.master)
	self.root.title("Traceback Dialog")
	self.label = Label(self.root, text="%s: %s" % (exc, str(val)))
	self.label.pack(fill=X)
	self.text, self.text_frame = tktools.make_text_box(self.root)
	self.close_button = Button(self.root,
				   text="Close",
				   command=self.close_command)
	self.close_button.pack()
	lines = traceback.format_exception(exc, val, tb)
	for line in lines:
	    self.text.insert(END, line + '\n')

    def close_command(self):
	self.root.destroy()
