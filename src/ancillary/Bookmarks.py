from Tkinter import *
import FileDialog
from grailutil import *
from Outliner import OutlinerNode, OutlinerViewer
import tktools
import formatter
import htmllib
import os
import string
import sys
import time


InGrail_p = __name__ != '__main__'


DEFAULT_NETSCAPE_BM_FILE = os.path.join(gethome(), '.netscape-bookmarks.html')
DEFAULT_GRAIL_BM_FILE = os.path.join(getgraildir(), 'grail-bookmarks.html')


True = 1
False = 0

BookmarkFormatError = 'BookmarkFormatError'
PoppedRootError = 'PoppedRootError'



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
	self._islink_p = not not uri_string
	self._isseparator_p = False

    def __repr__(self):
	return OutlinerNode.__repr__(self) + ' ' + self._title

    def title(self): return self._title
    def uri(self): return self._uri
    def add_date(self): return self._add_date
    def last_visited(self): return self._visited
    def description(self): return self._desc
    def islink_p(self): return self._islink_p

    def isseparator_p(self): return self._isseparator_p
    def set_separator(self):
	self._isseparator_p = True
	self._title = '------------------------------'

    def set_title(self, title=''): self._title = title
    def set_add_date(self, add_date=time.time()): self._add_date = add_date
    def set_last_visited(self, lastv): self._visited = lastv
    def set_description(self, description=''): self._desc = description
    def set_uri(self, uri_string=''):
	self._uri = uri_string
	self._islink_p = True



class HTMLBookmarkReader:
    def __init__(self, parser):
	self._parser = parser

    def read_file(self, fp):
	root = None
	try:
	    self._parser.feed(fp.read())
	    root = self._parser._root
	except IOError: pass
	return root

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



class NetscapeBookmarkHTMLParser(htmllib.HTMLParser):
    def __init__(self):
	self._root = None
	self._current = None
	self._prevleaf = None
	self._buffer = ''
	self._state = []
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

    def do_hr(self, attrs):
	snode = BookmarkNode()
	snode.set_separator()
	self._current.append_child(snode)

    def do_dd(self, attrs):
	self._buffer = ''
	self._state.append('dd')

    def ddpop(self, bl=0):
	if len(self._state) > 0 and self._state[-1] == 'dd':
	    self._prevleaf.set_description(self._buffer)
	    del self._state[-1]
	else:
	    htmllib.HTMLParser.ddpop(self, bl)

    def handle_data(self, data):
	if len(self._state) > 0 and self._state[-1] == 'dd':
	    self._buffer = self._buffer + data
	else:
	    htmllib.HTMLParser.handle_data(self, data)

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
	self._prevleaf = self._current
	self._pop()


class NetscapeBookmarkWriter:
    def _tab(self, node): return ' ' * (4 * node.depth())

    def _write_description(self, desc):
	if not desc: return
	# write the description, sans leading and trailing whitespace
	print '<DD>%s' % string.strip(desc)

    def _write_separator(self, node):
	print '%s<HR>' % self._tab(node)

    def _write_leaf(self, node):
	print '%s<DT><A HREF="%s" ADD_DATE="%d" LAST_VISIT="%d">%s</A>' % \
	      (self._tab(node), node.uri(), node.add_date(),
	       node.last_visited(), node.title())
	self._write_description(node.description())

    def _write_branch(self, node):
	tab = self._tab(node)
	print '%s<DT><H3 ADD_DATE="%d">%s</H3>' % \
	      (tab, node.add_date(), node.title())
	print '%s<DL><p>' % tab
	for child in node.children():
	    self._rwrite(child)
	print '%s</DL><p>' % tab

    def _write_header(self, root):
	print '<!DOCTYPE NETSCAPE-Bookmark-file-1>'
	print '<!-- This is an automatically generated file.'
	print '    It will be read and overwritten.'
	print '    Do Not Edit! -->'
	print '<TITLE>%s</TITLE>' % root.title()
	print '<H1>%s</H1>' % root.title()
	print '<DL><p>'

    def _rwrite(self, node):
	tab = '    ' * node.depth()
	if node.isseparator_p(): self._write_separator(node)
	elif node.leaf_p(): self._write_leaf(node)
	else:
	    self._write_branch(node)
	    print '%s<DL><p>' % tab
	    for child in node.children():
		self._rwrite(child)
	    print '%s</DL><p>' % tab

    def write_tree(self, root, filename):
	stdout = sys.stdout
	fp = None
	try:
	    fp = open(filename, 'w')
	    sys.stdout = fp
	    self._write_header(root)
	    for child in root.children():
		self._rwrite(child)
	    print '</DL><p>'
	finally:
	    if fp: fp.close()
	    sys.stdout = stdout


class GrailBookmarkHTMLParser(NetscapeBookmarkHTMLParser):
    def start_h3(self, attrs):
	self._push_new()
	self.save_bgn()
	for k, v in attrs:
	    if k == 'add_date': self._current.set_add_date(string.atoi(v))
	    elif k == 'expanded':
		if v: self._current.expand()
		else: self._current.collapse()

class GrailBookmarkWriter(NetscapeBookmarkWriter):
    def _write_header(self, root):
	print '<!DOCTYPE GRAIL-Bookmark-file-1>'
	print '<!-- This is an automatically generated file.'
	print '    It will be read and overwritten.'
	print '    Do Not Edit! -->'
	print '<TITLE>%s</TITLE>' % root.title()
	print '<H1>%s</H1>' % root.title()
	print '<DL><p>'

    def _write_branch(self, node):
	tab = self._tab(node)
	print '%s<DT><H3 ADD_DATE="%d" EXPANDED="%d">%s</H3>' % \
	      (tab, node.add_date(),
	       node.expanded_p() and 1 or 0,
	       node.title())


class TkListboxViewer(OutlinerViewer):
    def __init__(self, root, listbox):
	self._listbox = listbox
	OutlinerViewer.__init__(self, root)
	if len(self._nodes) > 0:
	    self.select_node(0)
	    self._listbox.activate(0)

    def populate(self):
	# we don't want the root node to show up
	for child in self._root.children():
	    OutlinerViewer._populate(self, child)

    def _insert(self, node, index=None):
	if index is None: index = 'end'
	self._listbox.insert(index, `node`)

    def _delete(self, start, end=None):
	if not end: self._listbox.delete(start)
	else: self._listbox.delete(start, end)

    def update_node(self, node):
	OutlinerViewer.update_node(self, node)
	index = node.index()
	self.select_node(index)
	self._listbox.activate(index)

    def select_node(self, index):
	self._listbox.select_clear(0, self.count())
	self._listbox.select_set(index)


class BMLoadDialog(FileDialog.LoadFileDialog):
    def __init__(self, master, controller):
	FileDialog.LoadFileDialog.__init__(self, master, 'Load Bookmarks File')
	self._controller = controller
	btnframe = Frame(self.top, relief='groove', borderwidth=2)
	btnframe.pack()
	frame1 = Frame(btnframe)
	frame1.pack(side='left')
	frame2 = Frame(btnframe)
	frame2.pack(side='left')
	label1 = Label(frame1, text='Bookmark File Shortcut:')
	label1.pack(anchor='e')
	label2 = Label(frame1, text='File Format:')
	label2.pack(anchor='e')
	frame3 = Frame(frame2)
	frame3.pack()
	grailbtn = Button(frame3, text='Grail',
			  command=self.set_for_grail)
	grailbtn.pack(anchor='w', side='left')
	netscapebtn = Button(frame3, text='Netscape',
			     command=self.set_for_netscape)
	netscapebtn.pack(side='left')
	formatbtn = OptionMenu(frame2,
			       controller.fileformat,
			       controller.fileformat.get(),
			       'Grail', 'Netscape')
	formatbtn.pack(anchor='w')

    def set_for_grail(self): pass
    def set_for_netscape(self): pass
    def show(self):
	self.top.deiconify()
	self.top.tkraise()

class BookmarksIO:
    def __init__(self, frame, controller):
	self._controller = controller
	self._frame = frame
	self._descriptor = None
	self._filename = None

    def _open_file_for_reading(self, filename, reader=None):
	try: fp = open(filename, 'r')
	except IOError: return (None, reader, None)
	if not reader:
	    # we may have to do more than this to figure out what
	    # format the bookmarks file is written in, but for now
	    # this works with Netscape v1 and Grail v1 style bookmark
	    # files.
	    import regex
	    line1 = fp.readline()
	    if regex.match('.*NETSCAPE-Bookmark-file-1', line1) >= 0:
		parser = NetscapeBookmarkHTMLParser()
		writer = NetscapeBookmarkWriter()
	    elif regex.match('.*GRAIL-Bookmark-file-1', line1) >= 0:
		parser = GrailBookmarkHTMLParser()
		writer = GrailBookmarkWriter()
	    else:
		raise BookmarkFormatError, \
		      'unknown bookmark file format for file %s' % \
		      filename
	    reader = HTMLBookmarkReader(parser)
	    # be sure to rewind the file
	    fp.seek(0)
	return (fp, reader, writer)

    def load(self):
	filename = self._filename
	# Semantics are: the first time this is called, self._file is
	# not set, so we want to simply load the default bookmarks
	# file.  We do not want to interact with the user at this
	# point.  Afterwards, we'll use the currently loaded filename
	# as the default, but we will prompt the user with the
	# FileLoadDialog.
	if not filename:
	    # default should be grail's bookmark file if it exists,
	    # otherwise use netscape's default bookmark file
	    if os.path.exists(DEFAULT_GRAIL_BM_FILE):
		filename = DEFAULT_GRAIL_BM_FILE
	    else: filename = DEFAULT_NETSCAPE_BM_FILE
	else:
	    loader = BMLoadDialog(self._frame, self._controller)
	    loader.show()
	    filename = loader.go(filename, '*.html')
	# now given a user selected filename, open it for reading,
	# then read it using the correct parser.
	if filename:
	    fp, reader, writer = self._open_file_for_reading(filename)
	    root = reader.read_file(fp)
	    fp.close()
	    self._filename = filename
	    return (root, reader, writer)
	else:
	    return (None, None, None)


class BookmarksController:
    def __init__(self, frame, browser):
	self._browser = browser
	self._frame = frame
	self._root = None
	self._viewer = None
	self._iomgr = BookmarksIO(frame, self)
	self._dialog = None
	self._details = {}
	self._tkvars = {
	    'aggressive': BooleanVar(),
	    'addcurloc':  IntVar(),
	    'fileformat': StringVar()
	    }
	self.aggressive.set(0)
	self.addcurloc.set(1)
	self.fileformat.set('Automatic')

    def __getattr__(self, name):
	if self._tkvars.has_key(name): return self._tkvars[name]
	else: raise AttributeError, name

    def _get_selected_node(self):
	list = self._listbox.curselection()
	if len(list) > 0:
	    selection = string.atoi(list[0])
	    return (self._viewer.node(selection), selection)
	else:
	    return (None, None)

    def set_listbox(self, listbox): self._listbox = listbox
    def set_dialog(self, dialog): self._dialog = dialog
    def set_bookmark_file(self, filename):
	self._bookmarkfile = filename
	self.load()

    def root(self): return self._root

    def select(self, event=None): pass

    def goto(self, event=None):
	node, selection = self._get_selected_node()
	self.goto_node(node)
    def bookmark_goto(self, event=None):
	self._browser.load('file:' + self._bookmarkfile)
    def goto_node(self, node):
	if node and node.leaf_p() and node.uri():
	    node.set_last_visited(int(time.time()))
	    if self._details.has_key(id(node)):
		self._details[id(node)].revert()
	    self._browser.load(node.uri())

    def _collapse_node(self, node):
	# This node is only collapsable if it is an unexpanded branch
	# node, or the aggressive collapse flag is set.
	uncollapsable = node.leaf_p() or not node.expanded_p()
	aggressive_p = self.aggressive.get()
	if uncollapsable and not aggressive_p:
	    return
	# if the node is a leaf and the aggressive collapse flag is
	# set, then we really need to find the start of the collapse
	# operation (some ancestor of the selected node)
	if uncollapsable: node = node.parent()
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
	if not end: end = self._viewer.count()
	self._viewer.delete_nodes(start, end)
	self._viewer.update_node(node)

    def _expand_node(self, node):
	# now toggle the expanded flag and update the listbox
	node.expand()
	# we need to recursively expand this node, based on each
	# sub-node's expand/collapse flag
	self._viewer.expand_node(node)
	self._viewer.update_node(node)

    def collapse(self, event=None):
	node, selection = self._get_selected_node()
	if node: self._collapse_node(node)

    def expand(self, event=None):
	node, selection = self._get_selected_node()
	# can't expand leaves or already expanded nodes
	if node and not node.leaf_p() and not node.expanded_p():
	    self._expand_node(node)

    def collapse_all(self, event=None):
	for child in self._root.children():
	    self._collapse_node(child)

    def expand_all(self, event=None):
	for child in self._root.children():
	    self._expand_node(child)

    def previous(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection > 0:
	    self._viewer.select_node(selection-1)

    def next(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection < self._viewer.count()-1:
	    self._viewer.select_node(selection+1)

    def load_without_show(self):
	self._root, reader, self._writer = self._iomgr.load()
	if self._root: return True
	else: return False
    def load(self, event=None):
	if self.load_without_show(): self.show()

    def merge(self, event=None): pass
    def save(self, event=None): self.saveas()

    def saveas(self, event=None):
	dialog = FileDialog.SaveFileDialog(self._frame)
	savefile = dialog.go(getgraildir(), '*.html')
	if savefile:
	    writer = GrailBookmarkWriter()
	    writer.write_tree(self._root, savefile)

    def add_current(self, event=None):
	# create a new node to represent this addition and then fit it
	# into the tree, updating the listbox
	see = True
	now = int(time.time())
	node = BookmarkNode(self._browser.title,
			    self._browser.url,
			    now, now)
	addlocation = self.addcurloc.get()
	if addlocation == 1:
	    # append this to the end of the list, which translates to:
	    # add this node to the end of root's child list.
	    lastnode = self._viewer.count()
	    self._root.append_child(node)
	    self._viewer.insert_nodes(lastnode, [node], True)
	elif addlocation == 2:
	    # prepend the node to the front of the list, which
	    # translates to: add this node to the beginning of root's
	    # child list.
	    self._root.insert_child(node, 0)
	    self._viewer.insert_nodes(0, [node], True)
	elif addlocation == 3:
	    # add current as child of selected node, which translates
	    # to: add this node to the end of the selected node's list
	    # of children.  The tricky bit is that we have to update
	    # the selected node, and we only want to display the new
	    # node in the listbox if the current selection is
	    # expanded.
	    snode, selection = self._get_selected_node()
	    if snode:
		children = snode.children()
		if children: insertion = children[-1].index()
		else: insertion = selection
		snode.append_child(node)
		if snode.expanded_p():
		    self._viewer.insert_nodes(insertion, [node])
		else:
		    see = False
		self._viewer.update_node(snode)
	else:
	    # really should raise an internal error or some such
	    pass
	if see: self._listbox.see(node.index())

    def update_node(self, node): self._viewer.update_node(node)

    def details(self, event=None):
	node, selection = self._get_selected_node()
	if not node or node.isseparator_p(): return
	if self._details.has_key(id(node)):
	    details = self._details[id(node)]
	    details.show()
	else:
	    details = DetailsDialog(Toplevel(self._frame), node, self)
	    self._details[id(node)] = details

    def show(self, event=None):
	if not self._dialog:
	    self._dialog = BookmarksDialog(self._frame, self)
	    self._listbox = self._dialog._listbox # TBD: gross
	if not self._viewer:
	    self._viewer = TkListboxViewer(self._root, self._listbox)
	    self._viewer.populate()
	self._dialog.show()

    def hide(self, event=None): self._dialog.hide()
    def quit(self, event=None): sys.exit(0)



class BookmarksDialog:
    def __init__(self, frame, controller):
	# create the basic controls of the dialog window
	self._frame = Toplevel(frame)
	self._controller = controller
	self._create_menubar()
	self._create_listbox()
	self._create_buttonbar()

    def _create_menubar(self):
	self._menubar = Frame(self._frame, relief=RAISED, borderwidth=2)
	self._menubar.pack(fill=X)
	# file menu
	filebtn = Menubutton(self._menubar, text="File")
	filebtn.pack(side=LEFT)
	filemenu = Menu(filebtn)
	filemenu.add_command(label="Load...",
			     command=self._controller.load,
			     underline=0, accelerator="Alt-L")
	self._frame.bind("<Alt-l>", self._controller.load)
	self._frame.bind("<Alt-L>", self._controller.load)
	filemenu.add_command(label="Merge...",
			     command=self._controller.merge,
			     underline=0, accelerator="Alt-M")
	self._frame.bind("<Alt-m>", self._controller.merge)
	# TBD: why can't I bind <Alt-M> here???!!!  I get a TclError...
	self._frame.bind("<Alt-Shift-m>", self._controller.merge)
	filemenu.add_command(label="Save",
			     command=self._controller.save,
			     underline=0, accelerator="Alt-S")
	self._frame.bind("<Alt-s>", self._controller.save)
	self._frame.bind("<Alt-S>", self._controller.save)
	filemenu.add_command(label="Save As...",
			     command=self._controller.saveas)
	filemenu.add_separator()
	filemenu.add_command(label="Close",
			     command=self._controller.hide,
			     underline=0, accelerator="Alt-W")
	self._frame.bind("<Alt-w>", self._controller.hide)
	self._frame.bind("<Alt-W>", self._controller.hide)
	filebtn.config(menu=filemenu)
	# navigation menu
	navbtn = Menubutton(self._menubar, text="Navigate")
	navbtn.pack(side=LEFT)
	navmenu = Menu(navbtn)
	navmenu.add_command(label="Previous",
			    command=self._controller.previous,
			    accelerator="Up")
	navmenu.add_command(label="Next",
			    command=self._controller.next,
			    accelerator="Down")
	navmenu.add_separator()
	navmenu.add_command(label="Go To Bookmark",
			    command=self._controller.goto,
			    underline=0, accelerator="Alt-G")
	self._frame.bind("<Alt-g>", self._controller.goto)
	self._frame.bind("<Alt-G>", self._controller.goto)
	navmenu.add_command(label="View in Grail",
			    command=self._controller.bookmark_goto,
			    underline=0, accelerator="Alt-V")
	self._frame.bind("<Alt-v>", self._controller.bookmark_goto)
	self._frame.bind("<Alt-V>", self._controller.bookmark_goto)
	navmenu.add_separator()
	navmenu.add_command(label="Expand",
			    command=self._controller.expand,
			    accelerator="Alt-E")
	self._frame.bind("<Alt-e>", self._controller.expand)
	self._frame.bind("<Alt-E>", self._controller.expand)
	navmenu.add_command(label="Collapse",
			    command=self._controller.collapse,
			    accelerator="Alt-C")
	self._frame.bind("<Alt-c>", self._controller.collapse)
	self._frame.bind("<Alt-C>", self._controller.collapse)
	navmenu.add_command(label="Expand Top Level",
			    command=self._controller.expand_all)
	navmenu.add_command(label="Collapse Top Level",
			    command=self._controller.collapse_all)
	navbtn.config(menu=navmenu)
	# Properties menu (details)
	propsbtn = Menubutton(self._menubar, text="Properties")
	propsbtn.pack(side=LEFT)
	propsmenu = Menu(propsbtn)
	propsmenu.add_checkbutton(label="Aggressive Collapse",
				  variable=self._controller.aggressive)
	propsmenu.add_separator()
	propsmenu.add_radiobutton(label='Add Current Appends to File',
				  variable=self._controller.addcurloc,
				  value=1)
	propsmenu.add_radiobutton(label='Add Current Prepends to File',
				  variable=self._controller.addcurloc,
				  value=2)
	propsmenu.add_radiobutton(label='Add Current As Child of Selection',
				  variable=self._controller.addcurloc,
				  value=3)
	propsbtn.config(menu=propsmenu)
	# edit menu
	editbtn = Menubutton(self._menubar, text="Edit")
	editbtn.pack(side=LEFT)
	editmenu = Menu(editbtn)
	editmenu.add_command(label="Bookmark Details...",
			     command=self._controller.details,
			     underline=0, accelerator="Alt-D")
	self._frame.bind("<Return>", self._controller.details)
	self._frame.bind("<Alt-d>", self._controller.details)
	self._frame.bind("<Alt-D>", self._controller.details)
	editmenu.add_separator()
	editmenu.add_command(label="Add Current",
			     command=self._controller.add_current,
			     underline=0, accelerator='Alt-A')
	self._frame.bind("<Alt-a>", self._controller.add_current)
	self._frame.bind("<Alt-A>", self._controller.add_current)
	editbtn.config(menu=editmenu)

    def _create_listbox(self):
	self._listbox, frame = tktools.make_list_box(self._frame,
						     60, 24, 1, 1)
	self._listbox.config(font='fixed')
	# bind keys
	self._listbox.bind('<Double-Button-1>', self._controller.goto)
	self._listbox.bind('<ButtonRelease-1>', self._controller.select)
	self._listbox.focus_set()

    def _create_buttonbar(self):
	# create the buttons
	btnframe = Frame(self._frame)
	prevbtn = Button(btnframe, text='Previous',
			 command=self._controller.previous)
	nextbtn = Button(btnframe, text='Next',
			 command=self._controller.next)
	prevbtn.pack(side='left')
	nextbtn.pack(side='left')

	if InGrail_p:
	    gotobtn = Button(btnframe, text='Go To',
			     command=self._controller.goto)
	    gotobtn.pack(side='left')

	colbtn = Button(btnframe, text='Collapse',
			command=self._controller.collapse)
	expbtn = Button(btnframe, text='Expand',
			command=self._controller.expand)

	colbtn.pack(side='left')
	expbtn.pack(side='left')

	if InGrail_p:
	    closebtn = Button(btnframe, text='Close',
			      command=self._controller.hide)
	    closebtn.pack(side='left')
	else:
	    quitbtn = Button(btnframe, text='Quit',
			     command=self._controller.quit)
	    quitbtn.pack(side='left')

	btnframe.pack(side='bottom')

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
	self._listbox.focus_set()

    def hide(self): self._frame.withdraw()



class DetailsDialog:
    def __init__(self, frame, node, controller):
	self._frame = frame
	self._node = node
	self._controller = controller
	self._create_form()
	self._create_buttonbar()

    def _create_form(self):
	make = tktools.make_labeled_form_entry # convenience
	self._form = [make(self._frame, 'Name', 40)]
	if self._node.islink_p():
	    self._form[1:] = [
		make(self._frame, 'Location', 40),
		make(self._frame, 'Last Visited', 40),
		make(self._frame, 'Added On', 40),
		make(self._frame, 'Description', 40, 5)
		]
	    self._form[2][0].config(relief='groove')
	    self._form[3][0].config(relief='groove')
	self.revert()

    def _create_buttonbar(self):
	btnbar = Frame(self._frame)
#	revertbtn = Button(btnbar, text='Revert',
#			   command=self.revert)
	donebtn = Button(btnbar, text='OK',
			 command=self.done)
	applybtn = Button(btnbar, text='Apply',
			  command=self.apply)
	cancelbtn = Button(btnbar, text='Cancel',
			   command=self.cancel)
#	revertbtn.pack(side='left')
	donebtn.pack(side='left')
	applybtn.pack(side='left')
	cancelbtn.pack(side='right')
	btnbar.pack(fill='both')

    def revert(self):
	# first we have to re-enable the read-only fields, otherwise
	# Tk will just ignore our updates.  blech!
	if self._node.islink_p():
	    for entry, frame, label in self._form[2:4]:
		entry.config(state='normal')
	# now empty out the text
	for entry, frame, label in self._form:
	    if type(entry) == type(()): entry[0].delete(1.0, 'end')
	    else: entry.delete(0, 'end')
	# fill in the entry fields
	node = self._node		# convenience
	self._form[0][0].insert(0, node.title())
	if node.islink_p():
	    self._form[1][0].insert(0, node.uri())
	    self._form[2][0].insert(0, time.ctime(node.last_visited()))
	    self._form[3][0].insert(0, time.ctime(node.add_date()))
	    self._form[4][0][0].insert(1.0, node.description())
	    # make the fields read-only again
	    for entry, frame, label in self._form[2:4]:
		entry.config(state='disabled')

    def apply(self):
	self._node.set_title(self._form[0][0].get())
	if self._node.islink_p():
	    self._node.set_uri(self._form[1][0].get())
	    self._node.set_description(self._form[4][0][0].get(1.0, 'end'))
	self._controller.update_node(self._node)

    def cancel(self):
	self.revert()
	self.hide()

    def done(self):
	self.apply()
	self.hide()

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()

    def hide(self): self._frame.withdraw()



class BookmarksMenuLeaf:
    def __init__(self, node, controller):
	self._node = node
	self._controller = controller
    def goto(self): self._controller.goto_node(self._node)

class BookmarksMenuViewer(OutlinerViewer):
    def __init__(self, controller, parentmenu):
	self._controller = controller
	self._depth = 0
	self._menustack = [parentmenu]
	root = controller.root()
	OutlinerViewer.__init__(self, controller.root())

    def populate(self):
	# don't want root node to show up in list
	for child in self._root.children():
	    OutlinerViewer._populate(self, child)

    def _insert(self, node, index=None):
	depth = node.depth()
	# this is the best way to pop the stack.  kinda kludgy...
	if depth < len(self._menustack):
	    del self._menustack[depth:]
	# get the current menu we're building
	menu = self._menustack[depth-1]
	if node.leaf_p():
	    leaf = BookmarksMenuLeaf(node, self._controller)
	    menu.add_command(label=node.title(), command=leaf.goto)
	else:
	    submenu = Menu(menu, tearoff='No')
	    self._menustack.append(submenu)
	    menu.add_cascade(label=node.title(), menu=submenu)

class BookmarksMenu:
    """This is top level hook between the Grail Browser and the
    Bookmarks subdialogs.  When invoked from within Grail, all
    functionality falls from this entry point.
    """
    def __init__(self, menu):
	self._menu = menu
	self._browser = menu.grail_browser
	self._frame = self._browser.root
	self._controller = BookmarksController(self._frame, self._browser)
	# currently, too difficult to coordinate edits to bookmarks
	# with tear-off menus, so just disable these for now and
	# create the rest of this menu every time the menu is posted
	self._menu.config(tearoff='No', postcommand=self.post)
	# fill in the static part of the menu
	self._menu.add_command(label='Add Current',
			       command=self._controller.add_current,
			       underline=0, accelerator='Alt-A')
	self._browser.root.bind('<Alt-a>', self._controller.add_current)
	self._browser.root.bind('<Alt-A>', self._controller.add_current)
 	self._menu.add_command(label='Bookmarks Viewer...',
			       command=self.show,
			       underline=0, accelerator='Alt-B')
	self._browser.root.bind('<Alt-b>', self.show)
	self._browser.root.bind('<Alt-B>', self.show)
	self._menu.add_separator()

    def post(self, event=None):
	# delete any old existing bookmark entries
	last = self._menu.index('end')
	if last > 2: self._menu.delete(3, 'end')
	# get the root of the current tree from the controller,
	# telling it to load the tree if necessary.
	if self._controller.root() or self._controller.load_without_show():
	    viewer = BookmarksMenuViewer(self._controller, self._menu)
	    viewer.populate()

    def show(self, event=None):
	if self._controller.root(): self._controller.show()
	else: self._controller.load()
