from Tkinter import *
from Outliner import OutlineNode
import tktools
import formatter
import htmllib
import os
import string
import sys
import time



class BookmarkNode(OutlineNode):
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
	OutlineNode.__init__(self)
	self._title = title
	self._uri = uri_string
	self._desc = description
	self._add_date = add_date
	self._visited = last_visited
	self._index = None

    def __repr__(self):
	return OutlineNode.__repr__(self) + ' ' + self._title

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


class TkListboxWriter:
    _gcounter = 0

    def __init__(self, root, listbox):
	self._root = root
	self._listbox = listbox
	self._nodes = []
	self._gcounter = 0
	self._populate(self._root)

    def _populate(self, node):
	# insert into linear list
	self._nodes.append(node)
	node.set_index(self._gcounter)
	self._gcounter = self._gcounter + 1
	# calculate the string to insert into the list box
	self._listbox.insert('end', `node`)
	for child in node.children():
	    self._populate(child)

    def insert_nodes(self, at_index, node_list, before_p=None):
	if not before_p: at_index = at_index + 1
	nodecount = len(node_list)
	for node in node_list:
	    self._nodes.insert(at_index, node)
	    self._listbox.insert(at_index, `node`)
	    node.set_index(at_index)
	    at_index = at_index + 1
	for node in self._nodes[at_index:]:
	    node.set_index(node.index() + nodecount)

    def delete_nodes(self, start, end):
	nodecount = end - start + 1
	self._listbox.delete(start, end)
	for node in self._nodes[end+1:]:
	    node.set_index(node.index() - nodecount)
	del self._nodes[start:end+1]

    def update_node(self, node):
	index = node.index()
	# TBD: is there a more efficient way of doing this!
	self._listbox.delete(index)
	self._listbox.insert(index, `node`)
	self._listbox.select_set(index)

    def node(self, index):
	if 0 <= index < len(self._nodes): return self._nodes[index]
	else: return None

    def count(self): return len(self._nodes)

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
	colbtn = Button(btnframe, text='Collapse', command=self.collapse)
	expbtn = Button(btnframe, text='Expand', command=self.expand)
	quitbtn = Button(btnframe, text='Quit', command=self.quit)
	colbtn.pack(side='left')
	expbtn.pack(side='left')
	quitbtn.pack(side='left')
	btnframe.pack(side='bottom')
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
	if (not node.leaf_p() and node.expanded_p()) or self._aggressive_p:
	    start = None
	    end = None
	    # find collapse extent
	    if node.leaf_p(): start = node.parent().index() + 1
	    else: start = node.index() + 1
	    # now that we know where to start, find out where to
	    # end. to do this we first find the node's next sibling
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
	    node.collapse()
	    self._writer.delete_nodes(start, end)
	    self._writer.update_node(node)

# TBD: we need to recursively expand based on the cached expand state!

    def expand(self):
	node, index = self._get_selected_node()
	# can't expand leaves or already expanded nodes
	if node.leaf_p() or node.expanded_p(): return
	# we expand so that only the most immediate children become visible
	self._writer.insert_nodes(index, node.children())
	# now toggle the expanded flag and update the listbox
	node.expand()
	self._writer.update_node(node)

    def quit(self): sys.exit(0)
    def run(self): self._tkroot.mainloop()



if __name__ == '__main__':
    bookmarks = BookmarkWindow("/tmp/test.html")
    bookmarks.run()
