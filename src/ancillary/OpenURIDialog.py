"""Modal dialog to prompt for a URI to open.
"""

from Tkinter import *
import tktools
import string

class OpenURIDialog:
    def __init__(self, master):
	self._frame = tktools.make_toplevel(master,
					    title="Open Location Dialog")
	self._entry, frame, label = tktools.make_labeled_form_entry(
	    self._frame, 'URI:', 40)
	self._entry.bind('<Return>', self.okay)
	btnframe = Frame(self._frame)
	btnframe.pack(fill=BOTH)
	okbtn = Button(btnframe, text='Ok', command=self.okay)
	okbtn.pack(side=LEFT)
	cancelbtn = Button(btnframe, text='Cancel', command=self.cancel)
	cancelbtn.pack(side=RIGHT)
	tktools.set_transient(self._frame, master)

	self._frame.protocol('WM_DELETE_WINDOW', self.cancel)
	self._frame.bind("<Alt-w>", self.cancel)
	self._frame.bind("<Alt-W>", self.cancel)

    def go(self):
	self._frame.grab_set()
	self._entry.focus_set()
	try:
	    self._frame.mainloop()
	except SystemExit, how:
	    self._frame.destroy()
	    return how

    def okay(self, event=None):
	uri = string.strip(self._entry.get())
	raise SystemExit, uri

    def cancel(self, event=None):
	raise SystemExit, None
