"""Data structure for History manipulation
"""

from Tkinter import *
import tktools
import string


class History:
    def __init__(self):
	self._history = []
	self._hmap = {}
	self._dialog = None

    def set_dialog(self, dialog): self._dialog = dialog

    def append_link(self, link, title=None):
	# don't add duplicate links to the history
	if self._hmap.has_key(link): return
	# add the link to the history structures
	self._history.append(link)
	if not title: title = link
	self._hmap[link] = title
	if self._dialog: self._dialog.append_link(link, title)

    def set_title(self, link, title):
	try:
	    if self._history[-1] != link or \
	       self._hmap[link] == title or \
	       link == title:
		return
	    # update title and dialog if visible
	    self._hmap[link] = title
	    if self._dialog: self._dialog.update(title)
	except IndexError, KeyError:
	    pass

    def title(self, link):
	try:
	    return self._hmap[link]
	except KeyError:
	    return None

    def link(self, index):
	if self._dialog: self._dialog.select(index)
	return self._history[index]

    def inhistory_p(self, link): return not not self.title(link)
    def links(self): return self._history


class HistoryDialog:
    def __init__(self, browser, historyobj=None, max=32):
	if not historyobj:
	    self._history = History()
	else:
	    self._history = historyobj
	# 
	self._browser = browser
	self._max = max
	self._history.set_dialog(self)
	self._frame = Toplevel(browser.root)
	self._vlinks = []
	self._viewby = IntVar()
	self._viewby.set(1)
	self._viewing = 1
	# create the UI elements
	self._listbox, frame = tktools.make_list_box(self._frame, 40, 24, 1, 1)
	self._mass_update()
	self._listbox.bind('<Double-Button-1>', self._goto)
	# add a couple of buttons
	btnbar = Frame(self._frame)
	btnbar.pack(fill=BOTH)
	gotobtn = Button(btnbar, text='Go To', command=self._goto)
	gotobtn.pack(side=LEFT)
	closebtn = Button(btnbar, text='Close', command=self._close)
	closebtn.pack(side=LEFT)
	# radio button for view option
	rbframe = Frame(btnbar)
	rbframe.pack()
	rb1 = Radiobutton(rbframe, text='View by titles',
			  command=self._viewby_command,
			  variable=self._viewby,
			  value=1)
	rb2 = Radiobutton(rbframe, text='View by URIs',
			  command=self._viewby_command,
			  variable=self._viewby,
			  value=2)
	rb1.pack(anchor='w')
	rb2.pack(anchor='w')
	    
    def history(self): return self._history

    def _mass_update(self):
	# populate listbox
	self._listbox.delete(0, 'end')
	# truncate list to max elements and view in reverse order
	hlist = self._history.links()
	if len(hlist) > self._max: hlist = hlist[-max]
	hlist.reverse()
	for link in hlist:
	    title = self._history.title(link)
	    if self._viewing == 1:
		self._listbox.insert('end', title)
	    elif self._viewing == 2:
		self._listbox.insert('end', link)
	    self._vlinks.append((link, title))

    def _goto(self, event=None):
	list = self._listbox.curselection()
	if len(list) > 0:
	    selection = string.atoi(list[0])
	    link, title = self._vlinks[selection]
	    self._browser.load(link)

    def _close(self, event=None):
	self._frame.withdraw()

    def _viewby_command(self, event=None):
	state = self._viewby.get()
	if state == self._viewing: return
	self._viewing = state
	self._mass_update()

    def append_link(self, link, title):
	if len(self._vlinks) > self._max:
	    del self._vlinks[-1]
	    self._listbox.delete('end')
	self._vlinks.insert(0, (link, title))
	if self._viewing == 1:
	    self._listbox.insert(0, title)
	elif self._viewing == 2:
	    self._listbox.insert(0, link)
	self.select(0)

    def update(self, title):
	if self._viewing == 1:
	    self._listbox.delete(0)
	    self._listbox.insert(0, title)

    def select(self, index):
	last = self._listbox.index('end')
	self._listbox.select_clear(0, 'end')
	self._listbox.select_set(last-index-1)
	self._listbox.activate(last-index-1)

    def show(self): self._frame.deiconify()
