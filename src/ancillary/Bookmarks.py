from Tkinter import *
from Outliner import OutlinerNode, OutlinerViewer
import tktools
import formatter
import htmllib
import os
import string
import sys
import time


InGrail_p = __name__ != '__main__'



class BookmarkNode(OutlinerNode):
    """Bookmarks are represented internally as a tree of nodes containing
    relevent information.

    Methods:

      title()        -- return title
      uri()          -- return URI string
      add_date()     -- return bookmark add timestamp
      last_visited() -- return last visited timestamp
      description()  -- return description string

        [[self explanatory??]]

      set_title(title)
      set_uri(uri_string)
      set_add_date(seconds)
      set_last_visited(seconds)
      set_description(string)

    Instance variables:

      No Public Ivars
    """

    def __init__(self, title='', uri_string = '',
		 add_date=time.time(), last_visited=time.time(),
		 description=''):
	OutlinerNode.__init__(self)
	self._title = title
	self._uri = uri_string
	self._desc = description
	self._add_date = add_date
	self._visited = last_visited
	self._index = None

    def __repr__(self):
	return OutlinerNode.__repr__(self) + ' ' + self._title

    def title(self): return self._title
    def uri(self): return self._uri
    def add_date(self): return self._add_date
    def last_visited(self): return self._visited
    def description(self): return self._desc

    def set_title(self, title=''): self._title = title
    def set_add_date(self, add_date=time.time()): self._add_date = add_date
    def set_last_visited(self, lastv=time.time()): self._visited = lastv
    def set_description(self, description=''): self._desc = description
    def set_uri(self, uri_string=''): self._uri = uri_string

    def index(self): return self._index
    def set_index(self, index): self._index = index


class DummyWriter(formatter.AbstractWriter):
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



PoppedRootError = 'PoppedRootError'

class NetscapeBookmarkHTMLParser(htmllib.HTMLParser):
    def __init__(self):
	self._root = None
	self._current = None
	w = DummyWriter()
	f = formatter.AbstractFormatter(w)
	htmllib.HTMLParser.__init__(self, f)

    def _push_new(self):
	newnode = BookmarkNode()
	self._current.append_child(newnode)
	self._current = newnode

    def _pop(self):
	if not self._current: raise PoppedRootError
	self._current = self._current.parent()

    def start_h1(self, attrs):
	self._root = self._current = BookmarkNode()
	self.save_bgn()

    def end_h1(self):
	title = self.save_end()
	self._current.set_title(title)

    def end_dl(self):
	self._pop()

    def start_h3(self, attrs):
	self._push_new()
	self.save_bgn()
	for k, v in attrs:
	    if k == 'add_date': self._current.set_add_date(string.atoi(v))

    def end_h3(self):
	title = self.save_end()
	self._current.set_title(title)

    def start_a(self, attrs):
	self._push_new()
	self.save_bgn()
	curnode = self._current		# convenience
	for k, v in attrs:
	    if k == 'href': curnode.set_uri(v)
	    elif k == 'add_date': curnode.set_add_date(string.atoi(v))
	    elif k == 'last_visit': curnode.set_last_visited(string.atoi(v))

    def end_a(self):
	title = self.save_end()
	self._current.set_title(title)
	self._pop()


class NetscapeBookmarkReader:
    def read_file(self, filename='~/.netscape-bookmarks.html'):
	parser = NetscapeBookmarkHTMLParser()
	root = None
	try:
	    fn = os.path.expanduser(filename)
	    fp = open(fn, 'r')
	    parser.feed(fp.read())
	    root = parser._root
	finally:
	    fp.close()
	return root


class TkListboxWriter(OutlinerViewer):
    _gcounter = 0

    def __init__(self, root, listbox):
	self._listbox = listbox
	OutlinerViewer.__init__(self, root)

    def _insert(self, node, index=None):
	if not index: index = 'end'
	self._listbox.insert(index, `node`)

    def _delete(self, start, end=None):
	if not end: self._listbox.delete(start)
	else: self._listbox.delete(start, end)

    def update_node(self, node):
	OutlinerViewer.update_node(self, node)
	self.select_node(node.index())

    def select_node(self, index):
	self._listbox.select_clear(0, self.count())
	self._listbox.select_set(index)



class BookmarkWindow:
    def __init__(self, filename):
	# this flag controls collapse of children.  it is either
	# aggressive or normal.  in aggressive mode, if a node is
	# collapsed that is either a leaf or an already collapsed
	# branch node, then the parent node is actually collapsed
	# instead.
	self._aggressive_p = 1
	# create basic Tk stuff
	tk = self._tkroot = Tk()
	# create the list box
	self._listbox, frame = tktools.make_list_box(tk, 80, 24, 1, 1)
	self._listbox.config(font='fixed')
	# create the buttons
	btnframe = Frame(tk)
	prevbtn = Button(btnframe, text='Previous', command=self.previous)
	nextbtn = Button(btnframe, text='Next', command=self.next)

	if InGrail_p:
	    gotobtn = Button(btnframe, text='Go To', command=self.goto)
	    quitbtn = Button(btnframe, text='Close', command=self.close)
	else:
	    quitbtn = Button(btnframe, text='Quit', command=self.quit)


	colbtn = Button(btnframe, text='Collapse', command=self.collapse)
	expbtn = Button(btnframe, text='Expand', command=self.expand)
	prevbtn.pack(side='left')
	nextbtn.pack(side='left')
	if InGrail_p:
	    gotobtn.pack(side='left')

	colbtn.pack(side='left')
	expbtn.pack(side='left')
	quitbtn.pack(side='left')
	btnframe.pack(side='bottom')
	# bind keys
	self._listbox.bind('<Key-Down>', self.next)
	self._listbox.bind('<Key-Up>', self.previous)
	self._listbox.bind('<Double-Button-1>', self.expand)
	self._listbox.focus_set()
	# populate the list box
	r = NetscapeBookmarkReader()
	self._noderoot = r.read_file(filename)
	self._writer = TkListboxWriter(self._noderoot, self._listbox)

    def set_aggressive_mode(self, flag):
	self._aggressive_p = flag

    def _get_selected_node(self):
	node = None
	selection = string.atoi(self._listbox.curselection()[0])
	node = self._writer.node(selection)
	return node, selection

    def collapse(self):
	node, selection = self._get_selected_node()
	# This node is only collapsable if it is an unexpanded branch
	# node, or the aggressive collapse flag is set.
	uncollapsable = node.leaf_p() or not node.expanded_p()
	if uncollapsable and not self._aggressive_p:
	    return
	# if the node is a leaf and the aggressive collapse flag is
	# set, then we really need to find the start of the collapse
	# operation (some ancestor of the selected node)
	if uncollapsable: node = node.parent()
	# don't collapse the root
	if node.index() == 0: return
	# find the start index
	node.collapse()
	start = node.index() + 1
	# Find the end
	end = None
	vnode = node
	pnode = node.parent()
	while not end and pnode:
	    sibs = pnode.children()
	    nextsib = sibs.index(vnode)
	    if nextsib+1 >= len(sibs):
		vnode = pnode
		pnode = vnode.parent()
	    else:
		end = sibs[nextsib+1].index() - 1
	# now that we have a valid start and end, delete!
	if not end: end = self._writer.count()
	self._writer.delete_nodes(start, end)
	self._writer.update_node(node)

    def expand(self, event=None):
	node, index = self._get_selected_node()
	# can't expand leaves or already expanded nodes
	if node.leaf_p() or node.expanded_p(): return
	# now toggle the expanded flag and update the listbox
	node.expand()
	# we need to recursively expand this node, based on each
	# sub-node's expand/collapse flag
	self._writer.expand_node(node)
	self._writer.update_node(node)

    def previous(self, event=None):
	node, index = self._get_selected_node()
	if index > 0: index = index - 1
	self._writer.select_node(index)

    def next(self, event=None):
	node, index = self._get_selected_node()
	if index < self._writer.count()-1: index = index + 1
	self._writer.select_node(index)

    def quit(self): sys.exit(0)
    def close(self): sys.exit(0)

    def run(self):
	self._writer.select_node(0)
	self._tkroot.mainloop()



if not InGrail_p:
    #bookmarks = BookmarkWindow("/tmp/test.html")
    bookmarks = BookmarkWindow("~/.netscape-bookmarks.html")
    bookmarks.run()
