"""Modal dialog to prompt for a URI to open.
"""

from Tkinter import *
import tktools
import string

class OpenURIDialog:
    def __init__(self, master):
	self._frame = tktools.make_toplevel(master,
					    title="Open Location Dialog")
	fr, top, btnframe = tktools.make_double_frame(
	    self._frame, relief=FLAT)
	self._entry, frame, label = tktools.make_labeled_form_entry(
	    top, 'URI:', 40)
	self._entry.bind('<Return>', self.okay)
	okbtn = Button(btnframe, text='Open', command=self.okay)
	newbtn = Button(btnframe, text='New', command=self.new)
	cancelbtn = Button(btnframe, text='Cancel', command=self.cancel)
	tktools.unify_button_widths(okbtn, newbtn, cancelbtn)
	okbtn.pack(side=LEFT)
	newbtn.pack(side=LEFT, padx='1m')
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
	except SystemExit, (uri, new):
	    self._frame.destroy()
	    if uri:
		uri = string.joinfields(string.split(uri), '')
	    return uri, new

    def okay(self, event=None):
	raise SystemExit, (self._entry.get(), 0)

    def new(self, event=None):
	raise SystemExit, (self._entry.get(), 1)

    def cancel(self, event=None):
	raise SystemExit, (None, 0)
