"""Data structures for History manipulation
"""

from Tkinter import *
import tktools
import string
import regex
import os
import sys
import time
from grailutil import *


class PageInfo:
    """This is the data structure used to represent a page in the
    History stack.  Each Browser object has it's own unique History
    stack which maintains volatile informatio about the page, to be
    restored when the page is re-visited via the history mechanism.
    For example, the state of any forms on the page, the entered and
    relocated URLs, or the scroll position are information that might
    be kept.

    A page can actually have 3 URL's associated with it.  First, the
    typed or clicked URL as it appears in the entry field or anchor,
    after relative URL resolution but before any server relocation
    errors.

    Second, the URL after relocation, possibly many steps of
    relocation.  Often this is to redirect a browser to the new
    location of a page, but more often it is to add a trailing slash
    on a page that lacks one.  In fact, there can be a relocation
    path, and you must watch for loops, but only the final resolved
    URL is of any significance.

    Third, if the pages contains a BASE tag, this URL is used in
    resolution of relative urls on this page.  Currently the baseurl
    information is kept with the browser object.
    """
    def __init__(self, url='', title='', scrollpos=None, formdata=[]):
	self._url = url
	self._title = title
	self._scrollpos = scrollpos
	self._formdata = formdata

    def set_url(self, url): self._url = url
    def set_title(self, title): self._title = title
    def set_scrollpos(self, scrollpos): self._scrollpos = scrollpos
    def set_formdata(self, formdata): self._formdata = formdata

    def url(self): return self._url
    def title(self): return self._title
    def scrollpos(self): return self._scrollpos
    def formdata(self): return self._formdata



class History:
    def __init__(self):
	class DummyDialog:
	    def refresh(self): pass
	    def select(self, index): pass

	self._history = []
	self._dialog = DummyDialog()
	self._current = 0

    def clone(self):
	newhist = History()
	newhist._history = self._history[:]
	newhist._current = self._current
	return newhist

    def set_dialog(self, dialog):
	self._dialog = dialog

    def append_page(self, pageinfo):
	# Discard alternative futures.  Someday we might have `Cactus
	# History' or we might expose the Global History to the user.
	del self._history[self._current+1:]
	# Don't append a duplicate of the last entry
	if not self._history or self._history[-1].url() <> pageinfo.url():
	    self._history.append(pageinfo)
	    self._current = len(self._history)-1
	self._dialog.refresh()

    def page(self, index=None):
	if index is None: index = self._current
	if 0 <= index < len(self._history):
	    self._current = index
	    self._dialog.select(self._current)
	    return self._history[self._current]
	else: return None

    def current(self): return self._current
    def forward(self): return self.page(self.current()+1)
    def back(self): return self.page(self.current()-1)
    def pages(self): return self._history
    def refresh(self): self._dialog.refresh()



class HistoryDialog:
    def __init__(self, browser, historyobj=None):
	if not historyobj:
	    self._history = History()
	else:
	    self._history = historyobj
	# 
	self._browser = browser
	self._history.set_dialog(self)
	self._frame = tktools.make_toplevel(self._browser.root,
					    title="History Dialog")
	self._viewby = IntVar()
	self._viewby.set(1)
	self._viewing = 1
	# add a couple of buttons
	btnbar = Frame(self._frame)
	btnbar.pack(fill=BOTH, side=BOTTOM)
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
	# create listbox
	self._listbox, frame = tktools.make_list_box(self._frame, 40, 24, 1, 1)
	self.refresh()
	self._listbox.config(takefocus=0, exportselection=0)
	self._listbox.bind('<Double-Button-1>', self._goto)
	# yes, yes, the mapping seems inverted, but it has to do with
	# the way history elements are displayed in reverse order in
	# the listbox...
	self._frame.bind("<Up>", self.next_cmd)
	self._frame.bind("p", self.next_cmd)
	self._frame.bind("P", self.next_cmd)
	self._frame.bind("<Down>", self.previous_cmd)
	self._frame.bind("n", self.previous_cmd)
	self._frame.bind("N", self.previous_cmd)
	tktools.set_transient(self._frame, self._browser.root)
	    
    def history(self): return self._history

    def refresh(self):
	# populate listbox
	self._listbox.delete(0, 'end')
	# view in reverse order
	pages = self._history.pages()[:]
	pages.reverse()
	for page in pages:
	    url = page.url()
	    title = page.title() or url
	    if self._viewing == 1:
		self._listbox.insert('end', title)
	    elif self._viewing == 2:
		self._listbox.insert('end', url)
	self.select(self._history.current())

    def previous_cmd(self, event=None):
	if self._history.back(): self._goto()
	else: self._frame.bell()
    def next_cmd(self, event=None):
	if self._history.forward(): self._goto()
	else: self._frame.bell()

    def _goto(self, event=None):
	list = self._listbox.curselection()
	if len(list) > 0:
	    selection = string.atoi(list[0])
	    last = self._listbox.index('end')
	    page = self._history.page(last - selection - 1)
	    if page: self._browser.load(page.url(), new=0)

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

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
