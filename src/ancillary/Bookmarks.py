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


# utilities bogusly copied from grail.py.  should be a util.py?
def getgraildir():
    return getenv("GRAILDIR") or os.path.join(gethome(), ".grail")

def gethome():
    try:
	home = getenv("HOME")
	if not home:
	    import pwd
	    user = getenv("USER") or getenv("LOGNAME")
	    if not user:
		pwent = pwd.getpwuid(os.getuid())
	    else:
		pwent = pwd.getpwnam(user)
	    home = pwent[6]
	return home
    except (KeyError, ImportError):
	return os.curdir

def getenv(s):
    if os.environ.has_key(s): return os.environ[s]
    return None


DEFAULT_NETSCAPE_BM_FILE = os.path.join(gethome(), '.netscape-bookmarks.html')
DEFAULT_GRAIL_BM_FILE = os.path.join(getgraildir(), '.grail-bookmarks.html')
DEFAULT_BOOKMARK_FILE = DEFAULT_NETSCAPE_BM_FILE

True = 1
False = 0



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
	self._islink_p = False

    def __repr__(self):
	return OutlinerNode.__repr__(self) + ' ' + self._title

    def title(self): return self._title
    def uri(self): return self._uri
    def add_date(self): return self._add_date
    def last_visited(self): return self._visited
    def description(self): return self._desc
    def islink_p(self): return self._islink_p

    def set_title(self, title=''): self._title = title
    def set_add_date(self, add_date=time.time()): self._add_date = add_date
    def set_last_visited(self, lastv=time.time()): self._visited = lastv
    def set_description(self, description=''): self._desc = description
    def set_uri(self, uri_string=''):
	self._uri = uri_string
	self._islink_p = True

    def index(self): return self._index
    def set_index(self, index): self._index = index


PoppedRootError = 'PoppedRootError'

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
    def read_file(self, filename):
	parser = NetscapeBookmarkHTMLParser()
	root = None
	fp = None
	try:
	    fp = open(filename, 'r')
	    parser.feed(fp.read())
	    root = parser._root
	finally:
	    if fp: fp.close()
	return root

class NetscapeBookmarkWriter:
    LEAF_FMT = '%s<DT><A HREF="%s" ADD_DATE="%d" LAST_VISIT="%d">%s</A>'
    BRANCH_FMT = '%s<DT><H3 ADD_DATE="%d">%s</H3>'

    def _rwrite(self, node):
	tab = '    ' * node.depth()
	if node.leaf_p():
	    print LEAF_FMT % (tab, node.uri(), node.add_date(),
			      node.last_visited(), node.title())
	    if node.description():
		print '<DD>%s' % node.description()
	else:
	    print BRANCH_FMT % (tab, node.add_date(), node.title())
	    print '%s<DL><p>' % tab

    def write_tree(self, root, filename):
	stdout = sys.stdout
	fp = None
	try:
	    fp = open(filename, 'w')
	    sys.stdout = fp
	    print '<!DOCTYPE NETSCAPE-Bookmark-file-1>'
	    print '<!-- This is an automatically generated file.'
	    print '    It will be read and overwritten.'
	    print '    Do Not Edit! -->'
	    print '<TITLE>%s</TITLE>' % root.title()
	    print '<H1>%s</H1>' % root.title()
	    print '<DL><p>'
	    self._rwrite(root)
	finally:
	    if fp: fp.close()
	    sys.stdout = stdout


class TkListboxWriter(OutlinerViewer):
    _gcounter = 0

    def __init__(self, root, listbox):
	self._listbox = listbox
	OutlinerViewer.__init__(self, root)
	self.select_node(0)

    def _insert(self, node, index=None):
	if not index: index = 'end'
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



class BookmarksController:
    def __init__(self, frame, browser):
	self._browser = browser
	self._frame = frame
	self._aggressive_var = BooleanVar()
	self._bookmarkfile = DEFAULT_BOOKMARK_FILE
	self._root = None
	self._writer = None
	self._details = {}

    def _get_selected_node(self):
	list = self._listbox.curselection()
	if len(list) > 0:
	    selection = string.atoi(list[0])
	    return (self._writer.node(selection), selection)
	else:
	    return None

    def set_listbox(self, listbox): self._listbox = listbox
    def set_dialog(self, dialog): self._dialog = dialog
    def set_bookmark_file(self, filename):
	self._bookmarkfile = filename
	self.load()

    def aggressive_var(self): return self._aggressive_var
    def root(self): return self._root

    def select(self, event=None): pass

    def goto(self, event=None):
	node, selection = self._get_selected_node()
	self.goto_node(node)
    def bookmark_goto(self, event=None):
	self._browser.load('file:' + self._bookmarkfile)
    def goto_node(self, node):
	if node and node.leaf_p() and node.uri():
	    self._browser.load(node.uri())

    def collapse(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	# This node is only collapsable if it is an unexpanded branch
	# node, or the aggressive collapse flag is set.
	uncollapsable = node.leaf_p() or not node.expanded_p()
	aggressive_p = self._aggressive_var.get()
	if uncollapsable and not aggressive_p:
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
	node, selection = self._get_selected_node()
	# can't expand leaves or already expanded nodes
	if not node or node.leaf_p() or node.expanded_p(): return
	# now toggle the expanded flag and update the listbox
	node.expand()
	# we need to recursively expand this node, based on each
	# sub-node's expand/collapse flag
	self._writer.expand_node(node)
	self._writer.update_node(node)

    def previous(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection > 0:
	    self._writer.select_node(selection-1)

    def next(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection < self._writer.count()-1:
	    self._writer.select_node(selection+1)

    def load(self, event=None):
	# TBD: need to figure out which file reader corresponds to the
	# bookmark ile we're reading
	reader = NetscapeBookmarkReader()
	self._root = reader.read_file(self._bookmarkfile)

    def merge(self, event=None): pass
    def save(self, event=None): pass
    def saveas(self, event=None): pass

    def add_current(self, event=None): pass
    def update_node(self, node): self._writer.update_node(node)

    def details(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	if self._details.has_key(id(node)):
	    details = self._details[id(node)]
	else:
	    details = DetailsDialog(Toplevel(self._frame), node, self)
	    self._details[id(node)] = details
	details.show()

    def show(self, event=None):
	if not self._writer:
	    self._writer = TkListboxWriter(self._root, self._listbox)
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
	filemenu.add_command(label="Merge...",
			     command=self._controller.merge,
			     underline=0, accelerator="Alt-M")
	filemenu.add_command(label="Save",
			     command=self._controller.save,
			     underline=0, accelerator="Alt-S")
	filemenu.add_command(label="Save As...",
			     command=self._controller.saveas,
			     underline=5, accelerator="Alt-A")
	filemenu.add_separator()
	filemenu.add_command(label="Close",
			     command=self._controller.hide,
			     underline=0, accelerator="Alt-Q")
	filebtn.config(menu=filemenu)
	# navigation menu
	navbtn = Menubutton(self._menubar, text="Navigate")
	navbtn.pack(side=LEFT)
	navmenu = Menu(navbtn)
	navmenu.add_command(label="Previous",
			    command=self._controller.previous,
			    accelerator="Key-Up")
	navmenu.add_command(label="Next",
			    command=self._controller.next,
			    accelerator="Key-Down")
	navmenu.add_separator()
	navmenu.add_command(label="Go To Bookmark",
			    command=self._controller.goto,
			    underline=0, accelerator="Alt-G")
	navmenu.add_command(label="View in Grail",
			    command=self._controller.bookmark_goto,
			    underline=0, accelerator="Alt-V")
	navmenu.add_separator()
	navmenu.add_command(label="Expand",
			    command=self._controller.expand,
			    accelerator="Key-Right")
	navmenu.add_command(label="Collapse",
			    command=self._controller.collapse,
			    accelerator="Key-Left")
	navbtn.config(menu=navmenu)
	# Properties menu (details)
	propsbtn = Menubutton(self._menubar, text="Properties")
	propsbtn.pack(side=LEFT)
	propsmenu = Menu(propsbtn)
	propsmenu.add_checkbutton(label="Aggressive Collapse",
				  variable=self._controller.aggressive_var())
	propsbtn.config(menu=propsmenu)
	# edit menu
	editbtn = Menubutton(self._menubar, text="Edit")
	editbtn.pack(side=LEFT)
	editmenu = Menu(editbtn)
	editmenu.add_command(label="Bookmark Details...",
			     command=self._controller.details,
			     underline=0, accelerator="Alt-D")
	editbtn.config(menu=editmenu)

    def _create_listbox(self):
	self._listbox, frame = tktools.make_list_box(self._frame,
						     60, 24, 1, 1)
	self._listbox.config(font='fixed')
	# bind keys
	self._listbox.bind('<Key-Down>', self._controller.next)
	self._listbox.bind('<Key-Up>', self._controller.previous)
	self._listbox.bind('<Key-Right>', self._controller.expand)
	self._listbox.bind('<Key-Left>', self._controller.collapse)
	self._listbox.bind('<Double-Button-1>', self._controller.details)
	self._listbox.bind('<ButtonRelease-1>', self._controller.select)
	self._listbox.focus_set()
	# connect to controller
	self._controller.set_listbox(self._listbox)

    def _create_buttonbar(self):
	# create the buttons
	btnframe = Frame(self._frame)
	prevbtn = Button(btnframe, text='Previous',
			 command=self._controller.previous)
	nextbtn = Button(btnframe, text='Next',
			 command=self._controller.next)

	if InGrail_p:
	    gotobtn = Button(btnframe, text='Go To',
			     command=self._controller.goto)
	else:
	    quitbtn = Button(btnframe, text='Quit',
			     command=self._controller.quit)

	colbtn = Button(btnframe, text='Collapse',
			command=self._controller.collapse)
	expbtn = Button(btnframe, text='Expand',
			command=self._controller.expand)
	prevbtn.pack(side='left')
	nextbtn.pack(side='left')
	if InGrail_p:
	    gotobtn.pack(side='left')

	colbtn.pack(side='left')
	expbtn.pack(side='left')

	if not InGrail_p:
	    quitbtn.pack(side='left')

	btnframe.pack(side='bottom')

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
	self._listbox.focus_set()

    def hide(self): self._frame.iconify()



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
	self.revert()

    def _create_buttonbar(self):
	btnbar = Frame(self._frame)
	revertbtn = Button(btnbar, text='Revert',
			   command=self.revert)
	applybtn = Button(btnbar, text='Apply',
			  command=self.apply)
	cancelbtn = Button(btnbar, text='Cancel',
			   command=self.cancel)
	donebtn = Button(btnbar, text='Done',
			 command=self.done)
	revertbtn.pack(side='left')
	applybtn.pack(side='left')
	cancelbtn.pack(side='left')
	donebtn.pack(side='left')
	btnbar.pack()

    def revert(self):
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
	    for entry, frame, label in self._form[2:3]:
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

    def hide(self): self._frame.iconify()



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

    def _insert(self, node, index=None):
	# forget about the root.  it's not useful
	depth = node.depth()
	if depth == 0: return
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
	self._dialog = None
	self._load_deferred_p = True
	# currently, too difficult to coordinate edits to bookmarks
	# with tear-off menus, so just disable these for now and
	# create the rest of this menu every time the menu is posted
	self._menu.config(tearoff='No', postcommand=self.post)
	# fill in the static part of the menu
	self._menu.add_command(label='Add Current',
			       command=self._controller.add_current,
			       underline=0, accelerator='Alt-A')
	self._browser.root.bind('<Alt-A>', self._controller.add_current)
 	self._menu.add_command(label='Bookmarks Viewer...',
			       command=self.show,
			       underline=0, accelerator='Alt-B')
	self._browser.root.bind('<Alt-B>', self.show)
	self._menu.add_separator()

    def _load(self):
	if self._load_deferred_p:
	    self._controller.load()
	    self._load_deferred_p = False

    def show(self, event=None):
	self._load()
	if not self._dialog:
	    self._dialog = BookmarksDialog(self._frame, self._controller)
	    self._controller.set_dialog(self._dialog)
	self._controller.show()

    def post(self, event=None):
	# delete any old existing bookmark entries
	last = self._menu.index('end')
	if last > 2: self._menu.delete(3, 'end')
	# now append all the bookmarks
	self._load()
	BookmarksMenuViewer(self._controller, self._menu)


if not InGrail_p:
    reader = NetscapeBookmarkReader()
    root = reader.read_file("~/.netscape-bookmarks.html")
    tkroot = Tk()
    bookmarks = BookmarkWindow(root, tkroot)
    tkroot.mainloop()
