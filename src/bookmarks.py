"""Bookmark reader/writer for Grail.
"""

from Tkinter import *
import tktools
import formatter
import htmllib
import os
import sys
import string
import time


# errors
Unimplemented = 'Unimplemented'
StackUnderflow = 'StackUnderflow'
LinkError = 'LinkError'



class BMNode:
    """Bookmarks are represented internally as a tree of nodes containing
    relevent information.  The current node definition is:

       Title       -- human readable text displayed for bookmark
       Link        -- URI, None, or a list of BMNode objects
       AddDate     -- Unix timestamp of when bookmark was added
       LastVisit   -- Unix timestamp of when bookmark was last followed
       Description -- human readable long description of bookmark
    """

    def __init__(self, Title='', Link=None,
		 AddDate=time.time(), LastVisit=time.time(),
		 Description=''):
	self._title = Title
	self._link = Link
	self._desc = Description
	self._add = AddDate
	self._visit = LastVisit

    def title(self): return self._title
    def link(self): return self._link
    def add_date(self): return self._add
    def last_visit(self): return self._visit
    def description(self): return self._desc

    def set_title(self, Title=''): self._title = Title
    def set_add_date(self, AddDate=time.time()): self._add = AddDate
    def set_last_visit(self, LastVisit=time.time()): self._visit = LastVisit
    def set_description(self, Description=''): self._desc = Description

    def append_link(self, Link):
	if type(Link) is type(''):
	    if self._link is None or type(self._link) == type(''):
		self._link = Link
	    else:
		raise LinkError, "Setting link list to string"
	elif self._link is None:
	    self._link = [Link]
	elif type(self._link) == type([]):
	    self._link.append(Link)
	else:
	    raise LinkError


class DevnullWriter(formatter.AbstractWriter):
    def new_font(self, font): pass
    def new_margin(self, margin, level): pass
    def new_spacing(self, spacing): pass
    def new_styles(self, styles): pass
    def send_paragraph(self, blankline): pass
    def send_line_break(self): pass
    def send_hor_rule(self): pass
    def send_label_data(self, data): pass
    def send_flowing_data(self, data): pass
    def send_literal_data(self, data): pass

class NetscapeBookmarkHTMLParser(htmllib.HTMLParser):
    def __init__(self):
	w = DevnullWriter()
	f = formatter.AbstractFormatter(w)
	htmllib.HTMLParser.__init__(self, f)

    def _push_new(self):
	newnode = BMNode()
	self.curnode.append_link(newnode)
	self.nodestack.append(newnode)
	self.curnode = newnode

    def _pop(self):
	del self.nodestack[-1]
	try: self.curnode = self.nodestack[-1]
	except IndexError: self.curnode = None

    def start_h1(self, attrs):
	self.root = BMNode()
	self.nodestack = [self.root]
	self.curnode = self.root
	self.save_bgn()

    def end_h1(self):
	title = self.save_end()
	self.curnode.set_title(title)

    def end_dl(self):
	self._pop()

    def start_h3(self, attrs):
	self._push_new()
	self.save_bgn()
	for k, v in attrs:
	    if k == 'add_date': self.curnode.set_add_date(string.atoi(v))

    def end_h3(self):
	title = self.save_end()
	self.curnode.set_title(title)

    def start_a(self, attrs):
	self._push_new()
	self.save_bgn()
	for k, v in attrs:
	    if k == 'href': self.curnode.append_link(v)
	    elif k == 'add_date': self.curnode.set_add_date(string.atoi(v))
	    elif k == 'last_visit': self.curnode.set_last_visit(string.atoi(v))

    def end_a(self):
	title = self.save_end()
	self.curnode.set_title(title)
	self._pop()

#    def handle_data(self, data):
#	print 'handle_data', data
	# we currently know that the only way to get here is if we've
	# seen a <dd> tag, which is the description of the current
	# node.
#	if self.curnode: self.curnode.set_description(data)

class NetscapeBookmarkReader:
    def __init__(self):
	self.p = NetscapeBookmarkHTMLParser()

    def read_file(self, filename='~/.netscape-bookmarks.html'):
	fn = os.path.expanduser(filename)
	try:
	    fp = open(fn, 'r')
	    self.p.feed(fp.read())
	    self.root = self.p.root
	finally:
	    fp.close()

	return self.root


class StdoutRawWriter:
    def __init__(self, root):
	self.root = root
	self.write_nodes(self.root, 0)

    def write_nodes(self, node, depth):
	tab = ' ' * (depth * 3)
	msg = tab + node.title()
	print msg
	if type(node.link()) == type([]):
	    for link in node.link():
		self.write_nodes(link, depth+1)


class TkRawWriter:
    def __init__(self, root, listbox):
	self.root = root
	self.listbox = listbox
	self.entries = []
	self.tab = '|___'
	self.openbranch = 'L___'
	self.closedbranch = '[___'
	self.leaf = '|___'
	self.write_nodes(self.root, 0)
	for e in self.entries:
	    self.listbox.insert('end', e)

    def write_nodes(self, node, depth):
	link = node.link()

	# doesn't yet handle collapsed branch nodes
	if link is None or type(link) == type(''): leaf_p = 1
	else: leaf_p = None

	if depth == 0:
	    entry = '+ ' + node.title()
	else:
	    entry = (leaf_p and self.leaf or self.openbranch) + \
		    (self.tab * max(0, depth-1)) + \
		    node.title()

	self.entries.append(entry)
	if not leaf_p:
	    for link in node.link():
		self.write_nodes(link, depth+1)


if __name__ == '__main__':
    r = NetscapeBookmarkReader()
    #StdoutRawWriter(r.read_file())

    root = Tk()
    listbox, frame = tktools.make_list_box(root, 80, 24, 1, 1)
    listbox.config(font='fixed')

    TkRawWriter(r.read_file(), listbox)

    btnframe = Frame(root)

    def quit(): sys.exit(0)

    quitbtn = Button(btnframe, text='Quit', command=quit)

    quitbtn.pack()
    btnframe.pack(side='bottom')

    root.mainloop()
