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

GRAIL_RE = regex.compile('\([^ \t]+\)[ \t]+\([^ \t]+\)[ \t]+?\(.*\)?')
DEFAULT_NETSCAPE_HIST_FILE = os.path.join(gethome(), '.netscape-history')
DEFAULT_GRAIL_HIST_FILE = os.path.join(getgraildir(), 'grail-history')

def now():
    return int(time.time())

class HistoryInfo:
    def __init__(self, link='', title='', timestamp=None, formdata=[]):
	# for convenience, and since this object is never exposed to
	# the upper layers, just make it's data members public.
	self.title = title
	self.link = link
	self.timestamp = timestamp or now()
	self.formdata = formdata


class HistoryLineReader:
    def _error(self, line):
	sys.stderr.write('WARNING: ignoring ill-formed history file line:\n')
	sys.stderr.write('WARNING: %s\n' % line)

class NetscapeHistoryReader(HistoryLineReader):
    def parse_line(self, line):
	try:
	    fields = string.splitfields(line, '\t')
	    link = string.strip(fields[0])
	    return HistoryInfo(link=link,
			       title=link,
			       timestamp=string.atoi(string.strip(fields[1]))
			       )
	except:
	    self._error(line)
	    return None

class GrailHistoryReader(HistoryLineReader):
    def parse_line(self, line):
	link = timestamp = title = ''
	try:
	    if GRAIL_RE.match(line) >= 0:
		link, ts, title = GRAIL_RE.group(1, 2, 3)
		return HistoryInfo(link=link,
				   title=title or link,
				   timestamp=string.atoi(string.strip(ts))
				   )
	except:
	    self._error(line)
	    return None

class HistoryReader:
    def read_file(self, fp, histobj):
	pass
	# read the first line, to determine what type of history file
	# we're looking at
	ghist = []
	line = fp.readline()
	if regex.match('GRAIL-global-history-file-1', line) >= 0:
	    linereader = GrailHistoryReader()
	elif regex.match('MCOM-Global-history-file-1', line) >= 0:
	    linereader = NetscapeHistoryReader()
	else:
	    return
	while line:
	    line = fp.readline()
	    if line:
		infonode = linereader.parse_line(line)
		if infonode:
		    ghist.append(infonode)
	# now mass update the history object
	histobj.mass_append(ghist)


class GlobalHistory:
    def __init__(self, app):
	self._app = app
	self._linkmap = {}
	self._history = []
    	# first try to load the Grail global history file
	fp = None
	try:
	    try: fp = open(DEFAULT_GRAIL_HIST_FILE)
	    except IOError:
		try: fp = open(DEFAULT_NETSCAPE_HIST_FILE)
		except IOError: pass
	    if fp:
		HistoryReader().read_file(fp, self)
	finally:
	    if fp: fp.close()
	app.register_on_exit(self.on_app_exit)

    def mass_append(self, histlist):
	histlist = histlist[:]
	histlist.reverse()
	for infonode in histlist:
	    self._linkmap[infonode.link] = infonode
	    self._history.append(infonode.link)

    def append_link(self, infonode):
	if not self._linkmap.has_key(infonode.link):
	    self._history.append(infonode.link)
	self._linkmap[infonode.link] = infonode

    def link(self, link):
	return self._linkmap.has_key(link) and self._linkmap[link]

    def links(self):
	return self._history[:]

    def on_app_exit(self):
	stdout = sys.stdout
	try:
	    fp = open(DEFAULT_GRAIL_HIST_FILE, 'w')
	    sys.stdout = fp
	    print 'GRAIL-global-history-file-1'
	    links = self.links()
	    links.reverse()
	    for link in links:
		n = self._linkmap[link]
		if n.title == n.link:
		    print '%s\t%d' % (n.link, n.timestamp)
		else:
		    print '%s\t%d\t%s' % (n.link, n.timestamp, n.title)
	finally:
	    sys.stdout = stdout
	    fp.close()
	self._app.unregister_on_exit(self.on_app_exit)



class History:
    def __init__(self, app):
	class DummyDialog:
	    def refresh(self): pass
	    def select(self, index): pass

	self._history = []
	self._dialog = DummyDialog()
	self._current = 0
	self._app = app
	# initialize global history the first time through
	try: self._ghistory = app.global_history
	except AttributeError:
	    self._ghistory = app.global_history = GlobalHistory(app)

    def clone(self):
	newhist = History(self._app)
	newhist._history = self._history[:]
	newhist._current = self._current
	return newhist

    def set_dialog(self, dialog):
	self._dialog = dialog

    def append_link(self, link, title=None):
	# Netscape-ism: Discard alternative future.  The Jump Trail
	# (Global History) should be exposed to the user, IMHO.
	del self._history[self._current+1:]
	# don't add duplicate of the last entry
	if len(self._history) > 0 and self._history[-1].link == link:
	    return
	infonode = HistoryInfo(link, title or link)
	self._history.append(infonode)
	self._current = len(self._history)-1
	self._ghistory.append_link(infonode)
	self._dialog.refresh()

    def set_title(self, link, title):
	infonode = self._ghistory.link(link)
	if infonode and infonode.title <> title and link <> title:
	    infonode.title = title
	    infonode.timestamp = now()
	    self._dialog.refresh()

    def title(self, link):
	infonode = self._ghistory.link(link)
	if infonode:
	    return infonode.title or infonode.link
	else:
	    return ''

    def set_formdata(self, link, data=[]):
	infonode = self._ghistory.link(link)
	if infonode:
	    infonode.formdata = data

    def formdata(self, link):
	# Netscapism: form data is associated with the stack, since as
	# the stack is cleared, so is form data.
	for n in self._history:
	    if n.link == link:
		return n.formdata
	return []

    def link(self, index=None):
	if index is None: index = self._current
	if 0 <= index < len(self._history):
	    self._current = index
	    self._dialog.select(self._current)
	    return self._history[self._current].link
	else: return None

    def inhistory_p(self, link):
	# horrible kludge is necessary because the link could be in
	# the history with or without a trailing slash.
	has_title = self.title(link) or self.title(link + '/')
	return not not has_title

    def current(self): return self._current
    def links(self): return map(lambda n: n.link, self._history)

    def forward(self): return self.link(self.current()+1)
    def back(self): return self.link(self.current()-1)



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
	hlist = self._history.links()
	hlist.reverse()
	for link in hlist:
	    title = self._history.title(link)
	    if self._viewing == 1:
		self._listbox.insert('end', title)
	    elif self._viewing == 2:
		self._listbox.insert('end', link)
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
	    link = self._history.link(last-selection-1)
	    if link: self._browser.load(link, new=0)

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
