"""Data structure for History manipulation
"""

from Tkinter import *
import tktools
import string


class History:
    def __init__(self, app):
	self._history = []
	self._hmap = {}
	self._dialog = None
	self._current = 0
	self._app = app
	app.register_on_exit(self.on_app_exit)

    def set_dialog(self, dialog): self._dialog = dialog

    def append_link(self, link, title=None):
	# Netscape-ism.  Discard alternative future.  TBD: IMHO bogus
	# semantics, since it loses complete historical trace
	del self._history[self._current+1:]
	# don't add duplicate the last entry
	try:
	    if self._history[-1] == link: return
	except IndexError: pass
	self._history.append(link)
	self._current = len(self._history)-1
	if not title: title = link
	if not self._hmap.has_key(link): self._hmap[link] = title
	if self._dialog: self._dialog.refresh()

    def set_title(self, link, title):
	try:
	    if self._history[-1] != link or \
	       self._hmap[link] == title or \
	       link == title:
		return
	    # update title and dialog if visible
	    self._hmap[link] = title
	    if self._dialog: self._dialog.refresh()
	except IndexError, KeyError:
	    pass

    def title(self, link):
	try: return self._hmap[link]
	except KeyError: return None

    def link(self, index=None):
	if not index: index = self._current
	if 0 <= index < len(self._history):
	    self._current = index
	    if self._dialog: self._dialog.select(self._current)
	    return self._history[self._current]
	else: return None

    def inhistory_p(self, link): return not not self.title(link)
    def links(self): return self._history
    def current(self): return self._current

    def forward(self): return self.link(self.current()+1)
    def back(self): return self.link(self.current()-1)

    def on_app_exit(self):
##	print 'history exiting...'
	self._app.unregister_on_exit(self.on_app_exit)



class HistoryDialog:
    def __init__(self, browser, historyobj=None):
	if not historyobj:
	    self._history = History()
	else:
	    self._history = historyobj
	# 
	self._browser = browser
	self._history.set_dialog(self)
	self._frame = Toplevel(browser.root)
	self._viewby = IntVar()
	self._viewby.set(1)
	self._viewing = 1
	# create the UI elements
	self._listbox, frame = tktools.make_list_box(self._frame, 40, 24, 1, 1)
	self.refresh()
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

    def refresh(self):
	# populate listbox
	self._listbox.delete(0, 'end')
	# view in reverse order
	hlist = self._history.links()[:]
	hlist.reverse()
	for link in hlist:
	    title = self._history.title(link)
	    if self._viewing == 1:
		self._listbox.insert('end', title)
	    elif self._viewing == 2:
		self._listbox.insert('end', link)
	self.select(self._history.current())

    def _goto(self, event=None):
	list = self._listbox.curselection()
	if len(list) > 0:
	    selection = string.atoi(list[0])
	    last = self._listbox.index('end')
	    link = self._history.link(last-selection-1)
	    if link: self._browser.load(link)

    def _close(self, event=None):
	self._frame.withdraw()

    def _viewby_command(self, event=None):
	state = self._viewby.get()
	if state == self._viewing: return
	self._viewing = state
	self.refresh()

    def select(self, index):
	last = self._listbox.index('end')
	self._listbox.select_clear(0, 'end')
	self._listbox.select_set(last-index-1)
	self._listbox.activate(last-index-1)

    def show(self): self._frame.deiconify()
