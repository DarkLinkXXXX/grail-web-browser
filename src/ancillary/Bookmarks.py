from Tkinter import *
import FileDialog
from grailutil import *
from Outliner import OutlinerNode, OutlinerViewer, OutlinerController
import tktools
import formatter
import htmllib
import os
import string
import sys
import time
import posix


InGrail_p = __name__ != '__main__'


DEFAULT_NETSCAPE_BM_FILE = os.path.join(gethome(), '.netscape-bookmarks.html')
DEFAULT_GRAIL_BM_FILE = os.path.join(getgraildir(), 'grail-bookmarks.html')

BOOKMARKS_FILES = [
    DEFAULT_GRAIL_BM_FILE,
    DEFAULT_NETSCAPE_BM_FILE,
    os.path.join(gethome(), '.netscape/bookmarks.html'), # Netscape 2.0
    ]

# allow for a separate environment variable GRAIL_BOOKMARKS_FILE, and
# search it first
try:
    file = os.environ['GRAIL_BOOKMARKS_FILE']
    file = os.path.expanduser(file)
    if file:
	BOOKMARKS_FILES.insert(0, file)
	if file <> DEFAULT_NETSCAPE_BM_FILE:
	    DEFAULT_GRAIL_BM_FILE = file
except KeyError:
    pass


True = 1
False = None

NEW_AT_END = 1
NEW_AT_BEG = 2
NEW_AS_CHILD = 3

BookmarkFormatError = 'BookmarkFormatError'
PoppedRootError = 'PoppedRootError'

def username():
    try: name = os.environ['NAME']
    except KeyError:
	import pwd
	name = pwd.getpwuid(posix.getuid())[4]
    return name



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
		 add_date=None, last_visited=None,
		 description=''):
	OutlinerNode.__init__(self)
	self._title = title
	self._uri = uri_string
	self._desc = description
	if add_date: self._add_date = add_date
	else: self._add_date = time.time()
	if last_visited: self._visited = last_visited
	else: self._visited = time.time()
	self._islink_p = not not uri_string
	self._isseparator_p = False
	if uri_string or last_visited: self._leaf_p = True
	else: self._leaf_p = False

    def __repr__(self):
	return OutlinerNode.__repr__(self) + ' ' + self.title()
    def leaf_p(self): return self._leaf_p

    def clone(self):
	newnode = BookmarkNode(self._title, self._uri, self._add_date,
			       self._visited, self._desc)
	# TBD: no good way to do this
	newnode._expanded_p = self._expanded_p
	newnode._depth = self._depth
	for child in self._children:
	    newchild = child.clone()
	    newchild._parent = newnode
	    newnode._children.append(newchild)
	# set derived class attributes
	newnode._islink_p = self._islink_p
	newnode._isseparator_p = self._isseparator_p
	newnode._leaf_p = self._leaf_p
	return newnode

    def append_child(self, node):
	OutlinerNode.append_child(self, node)
	self._leaf_p = False
    def insert_child(self, node, index):
	OutlinerNode.insert_child(self, node, index)
	self._leaf_p = False
    def del_child(self, node):
	rtnnode = OutlinerNode.del_child(self, node)
	if self._islink_p and len(self._children) == 0:
	    self._leaf_p = True
	return rtnnode

    def title(self): return self._title
    def uri(self): return self._uri
    def add_date(self): return self._add_date
    def last_visited(self): return self._visited
    def description(self): return self._desc
    def islink_p(self): return self._islink_p
    def isseparator_p(self): return self._isseparator_p

    def set_separator(self):
	self._isseparator_p = True
	self._leaf_p = True
	self._title = '------------------------------'

    def set_title(self, title=''): self._title = title
    def set_add_date(self, add_date=time.time()): self._add_date = add_date
    def set_last_visited(self, lastv):
	self._visited = lastv
	self._leaf_p = True

    def set_description(self, description=''): self._desc = description
    def set_uri(self, uri_string=''):
	self._uri = uri_string
	if uri_string:
	    self._islink_p = True
	    self._leaf_p = True



class HTMLBookmarkReader:
    def __init__(self, parser):
	self._parser = parser

    def read_file(self, fp):
	self._parser.feed(fp.read())
	return self._parser._root

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
	if not self._current: raise BookmarkFormatError, 'file corrupted'
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
	    elif k == 'folded': self._current.collapse()

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
	    if self._prevleaf:
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
	if node.expanded_p(): folded = ''
	else: folded = 'FOLDED '
	print '%s<DT><H3 %sADD_DATE="%d">%s</H3>' % \
	      (tab, folded, node.add_date(), node.title())

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

    def write_tree(self, root, fp):
	stdout = sys.stdout
	try:
	    sys.stdout = fp
	    self._write_header(root)
	    for child in root.children():
		self._rwrite(child)
	    print '</DL><p>'
	finally:
	    fp.close()
	    sys.stdout = stdout

class GrailBookmarkWriter(NetscapeBookmarkWriter):
    def _write_header(self, root):
	print '<!DOCTYPE GRAIL-Bookmark-file-1>'
	print '<!-- This is an automatically generated file.'
	print '    It will be read and overwritten.'
	print '    Do Not Edit!'
	print '    NOTE: This format is fully compatible with'
	print '          Netscape 1.x style bookmarks -->'
	print '<TITLE>%s</TITLE>' % root.title()
	print '<H1>%s</H1>' % root.title()
	print '<DL><p>'


class FileDialogExtras:
    def __init__(self, frame):
	# create a small subwindow for the extra buttons
	frame = Frame(frame, relief='groove', borderwidth=2)
	frame.pack()
	label = Label(frame, text='Bookmark File Shortcuts:')
	label.pack(side='left')
	grailbtn = Button(frame, text='Grail',
			  command=self.set_for_grail)
	grailbtn.pack(side='left')
	netscapebtn = Button(frame, text='Netscape',
			     command=self.set_for_netscape)
	netscapebtn.pack(side='left')

    def _set_to_file(self, path):
	dir, file = os.path.split(path)
	olddir, pat = self.get_filter()
	self.set_filter(dir, pat)
	self.set_selection(file)
	self.filter_command()

    def set_for_grail(self): self._set_to_file(DEFAULT_GRAIL_BM_FILE)
    def set_for_netscape(self): self._set_to_file(DEFAULT_NETSCAPE_BM_FILE)
	
class BMLoadDialog(FileDialog.LoadFileDialog, FileDialogExtras):
    def __init__(self, master, controller):
	self._controller = controller
	FileDialog.LoadFileDialog.__init__(self, master, 'Load Bookmarks File')
	FileDialogExtras.__init__(self, self.top)

class BMSaveDialog(FileDialog.SaveFileDialog, FileDialogExtras):
    def __init__(self, master, controller):
	self._controller = controller
	FileDialog.SaveFileDialog.__init__(self, master, 'Save Bookmarks File')
	FileDialogExtras.__init__(self, self.top)
    
class BookmarksIO:
    def __init__(self, frame, controller):
	self._controller = controller
	self._frame = frame
	self._descriptor = None
	self._filename = None

    def filename(self): return self._filename
    def set_filename(self, filename): self._filename = filename

    def _choose_reader_writer(self, fp):
	parser = writer = None
	try:
	    import regex
	    line1 = fp.readline()
	    if regex.match('.*NETSCAPE-Bookmark-file-1', line1) >= 0:
		parser = NetscapeBookmarkHTMLParser()
		writer = NetscapeBookmarkWriter()
	    elif regex.match('.*GRAIL-Bookmark-file-1', line1) >= 0:
		parser = NetscapeBookmarkHTMLParser()
		writer = GrailBookmarkWriter()
	finally:
	    fp.seek(0)
	# sanity checking
	if not parser or not writer:
	    raise BookmarkFormatError, 'unknown or missing bookmarks file'
	# create the reader
	reader = HTMLBookmarkReader(parser)
	return (reader, writer)

    def _open_file_for_reading(self, filename):
	reader = writer = None
	try:
	    fp = open(filename, 'r')
	    reader, writer = self._choose_reader_writer(fp)
	except IOError, error:
	    raise BookmarkFormatError, error
	return (fp, reader, writer)

    def load(self, usedefault=False):
	if self._filename: filename = self._filename
	else: filename = DEFAULT_GRAIL_BM_FILE
	if not usedefault:
	    loader = BMLoadDialog(self._frame, self._controller)
	    filename = loader.go(filename, '*.html')
	# load the file
	root = reader = writer = None
	if filename:
	    fp, reader, writer = self._open_file_for_reading(filename)
	    root = reader.read_file(fp)
	    fp.close()
	    self._filename = filename
	return (root, reader, writer)

    def _save_to_file_with_writer(self, writer, root, filename=None):
	try: posix.rename(filename, filename+'.bak')
	except posix.error: pass # no file to backup 
	fp = open(filename, 'w')
	writer.write_tree(root, fp)

    def save(self, writer, root):
	if not self._filename: self.saveas(writer, root)
	else: self._save_to_file_with_writer(writer, root, self._filename)

    def saveas(self, writer, root):
	if not self._filename: filename = DEFAULT_GRAIL_BM_FILE
	else: filename = self._filename
	saver = BMSaveDialog(self._frame, self._controller)
	savefile = saver.go(filename, '*.html')
	if savefile:
	    self._save_to_file_with_writer(writer, root, savefile)
	    self._filename = savefile

class IOErrorDialog:
    def __init__(self, master, where, errmsg):
	msg = 'Bookmark file error encountered %s:' % where
	self._frame = tktools.make_toplevel(master, msg)
	label = Label(self._frame, text=msg)
	label.pack()
	errlabel = Label(self._frame, text=errmsg)
	errlabel.pack()
	self.closebtn = Button(self._frame, text="OK", command=self.close)
	self.closebtn.pack()
	self._frame.grab_set()

    def close(self): self._frame.destroy()



class TkListboxViewer(OutlinerViewer):
    def __init__(self, root, listbox):
	self._listbox = listbox
	OutlinerViewer.__init__(self, root)
	if len(self._nodes) > 0:
	    self.select_node(0)
	    self._listbox.activate(0)

    def _clear(self):
	self._listbox.delete(0, END)

    def _insert(self, node, index=None):
	if index is None: index = 'end'
	self._listbox.insert(index, `node`)

    def _delete(self, start, end=None):
	if not end: self._listbox.delete(start)
	else: self._listbox.delete(start, end)

    def _select(self, index):
	last = self._listbox.index(END)
	if not (0 <= index < last): index = 0
	self._listbox.select_clear(0, END)
	self._listbox.select_set(index)
	self._listbox.activate(index)
	self._listbox.see(index)


class BookmarksDialog:
    def __init__(self, frame, controller):
	# create the basic controls of the dialog window
	self._frame = Toplevel(frame, class_='Grail')
	self._controller = controller
	infoframe = Frame(self._frame, relief=GROOVE, borderwidth=2)
	infoframe.pack(fill=BOTH)
	self._title = Label(infoframe, text=controller.root().title())
	self._title.pack(fill=BOTH)
	self._file = Label(infoframe, text=controller.filename())
	self._file.pack(fill=BOTH)
	self._create_menubar()
	self._create_buttonbar()
	self._create_listbox()

    def _create_menubar(self):
	self._menubar = Frame(self._frame, relief=RAISED, borderwidth=2)
	self._menubar.pack(fill=X)
	# file menu
	filebtn = Menubutton(self._menubar, text="File")
	filebtn.pack(side=LEFT)
	filemenu = Menu(filebtn)
	filemenu.add_command(label="Load...",
			     command=self.load,
			     underline=0, accelerator="Alt-L")
	self._frame.bind("<Alt-l>", self.load)
	self._frame.bind("<Alt-L>", self.load)
#	filemenu.add_command(label="Merge...",
#			     command=self._controller.merge,
#			     underline=0, accelerator="Alt-M")
#	self._frame.bind("<Alt-m>", self._controller.merge)
	# TBD: why can't I bind <Alt-M> here???!!!  I get a TclError...
#	self._frame.bind("<Alt-Shift-m>", self._controller.merge)
	filemenu.add_command(label="Save",
			     command=self._controller.save,
			     underline=0, accelerator="Alt-S")
	self._frame.bind("<Alt-s>", self._controller.save)
	self._frame.bind("<Alt-S>", self._controller.save)
	filemenu.add_command(label="Save As...",
			     command=self._controller.saveas)
	filemenu.add_command(label="View Bookmarks in Grail",
			     command=self._controller.bookmark_goto,
			     underline=0, accelerator="Alt-V")
	self._frame.bind("<Alt-v>", self._controller.bookmark_goto)
	self._frame.bind("<Alt-V>", self._controller.bookmark_goto)
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
			    command=self._controller.previous_cmd,
			    accelerator="Up")
	self._frame.bind("<Up>", self._controller.previous_cmd)
	self._frame.bind("p", self._controller.previous_cmd)
	self._frame.bind("P", self._controller.previous_cmd)
	navmenu.add_command(label="Next",
			    command=self._controller.next_cmd,
			    accelerator="Down")
	self._frame.bind("<Down>", self._controller.next_cmd)
	self._frame.bind("n", self._controller.next_cmd)
	self._frame.bind("N", self._controller.next_cmd)
	navmenu.add_separator()
	navmenu.add_command(label="Go To Bookmark",
			    command=self._controller.goto,
			    underline=0, accelerator="G")
	self._frame.bind("g", self._controller.goto)
	self._frame.bind("G", self._controller.goto)
	self._frame.bind("<KeyPress-space>", self._controller.goto)
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
				  value=NEW_AT_END)
	propsmenu.add_radiobutton(label='Add Current Prepends to File',
				  variable=self._controller.addcurloc,
				  value=NEW_AT_BEG)
	propsmenu.add_radiobutton(label='Add Current As Child or Sibling',
				  variable=self._controller.addcurloc,
				  value=NEW_AS_CHILD)
	propsbtn.config(menu=propsmenu)
	# edit menu
	editbtn = Menubutton(self._menubar, text="Edit")
	editbtn.pack(side=LEFT)
	editmenu = Menu(editbtn)
	editmenu.add_command(label="Add Current",
			     command=self._controller.add_current,
			     underline=0, accelerator='Alt-A')
	self._frame.bind("<Alt-a>", self._controller.add_current)
	self._frame.bind("<Alt-A>", self._controller.add_current)
	editmenu.add_command(label="Bookmark Details...",
			     command=self._controller.details,
			     underline=0, accelerator="Alt-D")
	self._frame.bind("<Alt-d>", self._controller.details)
	self._frame.bind("<Alt-D>", self._controller.details)
	editmenu.add_separator()
	editmenu.add_command(label="Expand",
			    command=self._controller.expand_cmd,
			    underline=0, accelerator="E")
	self._frame.bind("e", self._controller.expand_cmd)
	self._frame.bind("E", self._controller.expand_cmd)
	editmenu.add_command(label='Expand All Children',
			     command=self._controller.expand_children)
	editmenu.add_command(label="Expand Top Level",
			    command=self._controller.expand_top)
#	editmenu.add_command(label="Expand All",
#			    command=self._controller.expand_all)
	editmenu.add_separator()
	editmenu.add_command(label="Collapse",
			    command=self._controller.collapse_cmd,
			    underline=0, accelerator="C")
	self._frame.bind("c", self._controller.collapse_cmd)
	self._frame.bind("C", self._controller.collapse_cmd)
	editmenu.add_command(label='Collapse All Children',
			     command=self._controller.collapse_children)
	editmenu.add_command(label="Collapse Top Level",
			    command=self._controller.collapse_top)
#	editmenu.add_command(label="Collapse All",
#			    command=self._controller.collapse_all)
	editmenu.add_separator()
	editmenu.add_command(label='Insert Separator',
			     command=self._controller.insert_separator,
			     underline=7, accelerator='S')
	self._frame.bind('s', self._controller.insert_separator)
	self._frame.bind('S', self._controller.insert_separator)
	editmenu.add_command(label='Insert Header',
			     command=self._controller.insert_header,
			     underline=7, accelerator='H')
	self._frame.bind('h', self._controller.insert_header)
	self._frame.bind('H', self._controller.insert_header)
	editmenu.add_command(label='Insert Link Entry',
			     command=self._controller.insert_entry,
			     underline=10, accelerator='K')
	self._frame.bind('k', self._controller.insert_entry)
	self._frame.bind('K', self._controller.insert_entry)
	editmenu.add_separator()
	editmenu.add_command(label='Remove Entry',
			     command=self._controller.remove_entry,
			     accelerator='X')
	self._frame.bind('x', self._controller.remove_entry)
	self._frame.bind('X', self._controller.remove_entry)
	editmenu.add_separator()
	editmenu.add_command(label='Shift Entry Left',
			     command=self._controller.shift_left_cmd,
			     underline=12, accelerator='L')
	self._frame.bind('l', self._controller.shift_left_cmd)
	self._frame.bind('L', self._controller.shift_left_cmd)
	editmenu.add_command(label='Shift Entry Right',
			     command=self._controller.shift_right_cmd,
			     underline=12, accelerator='R')
	self._frame.bind('r', self._controller.shift_right_cmd)
	self._frame.bind('R', self._controller.shift_right_cmd)
	editmenu.add_command(label='Shift Entry Up',
			     command=self._controller.shift_up_cmd,
			     underline=12, accelerator='U')
	self._frame.bind('u', self._controller.shift_up_cmd)
	self._frame.bind('U', self._controller.shift_up_cmd)
	editmenu.add_command(label='Shift Entry Down',
			     command=self._controller.shift_down_cmd,
			     underline=12, accelerator='D')
	self._frame.bind('d', self._controller.shift_down_cmd)
	self._frame.bind('D', self._controller.shift_down_cmd)
	editbtn.config(menu=editmenu)

    def _create_listbox(self):
	self._listbox, frame = tktools.make_list_box(self._frame,
						     60, 24, 1, 1)
	self._listbox.config(font='fixed')
	# bind keys
	self._listbox.bind('<Double-Button-1>', self._controller.goto)
	self._listbox.config(takefocus=0, exportselection=0)

    def _create_buttonbar(self):
	# create the button bars
	btmframe = Frame(self._frame)
	btmframe.pack(side=BOTTOM, fill=BOTH)
	topframe = Frame(self._frame)
	topframe.pack(side=BOTTOM, fill=BOTH)
	# bottom buttonbar buttons
	okbtn = Button(btmframe, text='OK', command=self.okay_cmd)
	okbtn.pack(side=LEFT)
	savebtn = Button(btmframe, text='Save', command=self.save_cmd)
	savebtn.pack(side=LEFT)
	self._frame.bind("<Return>", self.okay_cmd)
	status = Label(btmframe, text='', foreground='Red', anchor='w',
		       textvariable=self._controller.statusmsg)
	status.pack(side=LEFT, expand=1, fill=BOTH)
	cancelbtn = Button(btmframe, text='Cancel', command=self.cancel_cmd)
	cancelbtn.pack(side=RIGHT)
	# top buttonbar buttons
	prevbtn = Button(topframe, text='Previous',
			 command=self._controller.previous_cmd)
	nextbtn = Button(topframe, text='Next',
			 command=self._controller.next_cmd)
	prevbtn.pack(side=LEFT, expand=1, fill=BOTH)
	nextbtn.pack(side=LEFT, expand=1, fill=BOTH)
	gotobtn = Button(topframe, text='Go To',
			 command=self._controller.goto)
	gotobtn.pack(side=LEFT, expand=1, fill=BOTH)
	colbtn = Button(topframe, text='Collapse',
			command=self._controller.collapse_cmd)
	expbtn = Button(topframe, text='Expand',
			command=self._controller.expand_cmd)
	colbtn.pack(side=LEFT, expand=1, fill=BOTH)
	expbtn.pack(side=LEFT, expand=1, fill=BOTH)

    def set_modflag(self, flag):
	if flag: text = '<===== Changes are unsaved!'
	else: text = ''
	self._controller.statusmsg.set(text)

    def load(self, event=None):
	try:
	    self._controller.load()
	except (IOError, BookmarkFormatError), errmsg:
	    IOErrorDialog(self._frame, 'during loading', errmsg)

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()

    def save_cmd(self, event=None):
	self._controller.save()
    def okay_cmd(self, event=None):
	self._controller.save()
	self._controller.hide()
    def cancel_cmd(self, event=None):
	self._controller.revert()
	self._controller.hide()
    def hide(self): self._frame.withdraw()

    def set_labels(self, filename, title):
	self._file.config(text=filename)
	self._title.config(text=title)


class DetailsDialog:
    def __init__(self, master, node, controller):
	self._frame = Toplevel(master, class_='Grail')
	self._frame.title("Bookmark Details")
	self._frame.iconname("Bookmark Details")
	self._node = node
	self._controller = controller
	self._create_form()
	self._create_buttonbar()
	self._frame.bind('<Return>', self.done)

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
	entry = self._form[0][0]	# more convenience
	entry.insert(0, node.title())
	entry.select_range(0, END)
	entry.focus_set()
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
	self._controller.viewer().update_node(self._node)
	self._controller.viewer().select_node(self._node)
	self._controller.set_modflag(True)

    def cancel(self):
	self.revert()
	self.hide()

    def done(self, event=None):
	self.apply()
	self.hide()

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()

    def hide(self): self._frame.withdraw()
    def destroy(self): self._frame.destroy()



class BookmarksController(OutlinerController):
    def __init__(self, frame, app):
	default_root = BookmarkNode(username()+"'s Bookmarks")
	OutlinerController.__init__(self, default_root)
	self._frame = frame
	self._app = app
	self._active = None
	self._iomgr = BookmarksIO(frame, self)
	self._dialog = None
	self._details = {}
	self._listbox = None
	self._writer = GrailBookmarkWriter()
	self._initialized_p = False
	self._tkvars = {
	    'aggressive': BooleanVar(),
	    'addcurloc':  IntVar(),
	    'fileformat': StringVar(),
	    'statusmsg': StringVar(),
	    }
	self.aggressive.set(0)
	self.addcurloc.set(NEW_AT_BEG)
	self.fileformat.set('Automatic')
	self.statusmsg.set('')
	self._modflag = False
	from __main__ import app
	self._app = app
	app.register_on_exit(self.on_app_exit)

    def __getattr__(self, name):
	if self._tkvars.has_key(name): return self._tkvars[name]
	else: raise AttributeError, name

    def _browser(self):
	browser = self._active
	try: self._app.browsers.index(browser)
	except ValueError: browser = None
	return browser

    ## coordinate with Application instance

    def on_app_exit(self):
	if self._modflag: self.save(exiting=True)
	self._app.unregister_on_exit(self.on_app_exit)

    ## Modifications updating
    def set_modflag(self, flag, quiet=False):
	if self._dialog and not quiet:
	    self._dialog.set_modflag(flag)
	self._modflag = flag

    ## I/O

    def initialize(self, active_browser=None):
	if active_browser: self._active = active_browser
	if self._initialized_p: return
	# attempt to read each bookmarks file in the BOOKMARKS_FILES
	# list.  Search order is 1) $GRAIL_BOOKMARKS_FILE; 2)
	# $GRAIL_DIR/grail-bookmarks.html; 3) ~/.netscape-bookmarks.html
	root = None
	for file in BOOKMARKS_FILES[:]:
	    self._iomgr.set_filename(file)
	    try:
		root, reader, self._writer = self._iomgr.load(True)
		break
	    except BookmarkFormatError:
		pass
	if not root:
	    root = BookmarkNode(username()+"'s Bookmarks")
	    self._writer = GrailBookmarkWriter()
	    self._iomgr.set_filename(DEFAULT_GRAIL_BM_FILE)
	self.set_root(root)
	self._initialized_p = True

    def _on_new_root(self):
	for dialog in self._details.values(): dialog.destroy()
	self._details = {}
	self.set_viewer(TkListboxViewer(self.root(), self._listbox))
	self.root_redisplay()
	# set up new state
	node = self.viewer().node(0)
	self.set_modflag(False)
	if node: self.viewer().select_node(node)

    def load(self, usedefault=False):
	root, reader, writer = self._iomgr.load(usedefault=usedefault)
	if not root and not reader and not writer:
	    # load dialog was cancelled
	    return
	self._writer = writer
	self._dialog.set_labels(self._iomgr.filename(), self._root.title())
	# clear out all the old state
	self.set_root(root)
	self._on_new_root()

    def revert(self):
	OutlinerController.revert(self)
	self._on_new_root()

##    def merge(self, event=None): pass
    def save(self, event=None, exiting=False):
	# if it hasn't been modified, it doesn't need saving
	if not self.set_modflag: return
	self._iomgr.save(self._writer, self._root)
	self.set_modflag(False)
	self.update_backup()
	if self._dialog and not exiting:
	    self._dialog.set_labels(self._iomgr.filename(), self._root.title())

    def saveas(self, event=None):
	# always save-as, even if unmodified
	self._iomgr.saveas(self._writer, self._root)
	self.set_modflag(False)
	self.update_backup()
	if self._dialog:
	    self._dialog.set_labels(self._iomgr.filename(), self._root.title())

    ## Other commands

    def set_listbox(self, listbox): self._listbox = listbox
    def set_dialog(self, dialog): self._dialog = dialog
    def filename(self): return self._iomgr.filename()

    def _get_selected_node(self):
	node = selection = None
	try:
	    list = self._listbox.curselection()
	    if len(list) > 0:
		selection = string.atoi(list[0])
		return self.viewer().node(selection), selection
	except AttributeError: pass
	return node, selection

    def goto(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	if node.leaf_p():
	    self.goto_node(node)
	else:
	    if node.expanded_p(): self.collapse_node(node)
	    else: self.expand_node(node)
	    self.viewer().select_node(node)
	    self.set_modflag(True, quiet=True)

    def bookmark_goto(self, event=None):
	filename = self._iomgr.filename()
	if filename: self._browser().load('file:' + filename)
    def goto_node(self, node):
	if node and node.leaf_p() and node.uri():
	    node.set_last_visited(int(time.time()))
	    if self._details.has_key(id(node)):
		self._details[id(node)].revert()
	    self._browser().load(node.uri())
	    self.viewer().select_node(node)
	    self.set_modflag(True, quiet=True)

    def add_current(self, event=None):
	# create a new node to represent this addition and then fit it
	# into the tree, updating the listbox
	now = int(time.time())
	browser = self._browser()
	node = BookmarkNode(browser.title, browser.url, now, now)
	addlocation = self.addcurloc.get()
	if addlocation == NEW_AT_END:
	    # add this node to the end of root's child list.
	    self.root().append_child(node)
	elif addlocation == NEW_AT_BEG:
	    # add this node to the beginning of root's child list.
	    self.root().insert_child(node, 0)
	elif addlocation == NEW_AS_CHILD:
	    # if the node is a branch, add the new node to the end of
	    # it's child list.  if it is a leaf, add it as a sibling
	    # of the selected node.
	    snode, selection = self._get_selected_node()
	    # if no node was selected, then just insert it at the top.
	    if not snode:
		snode = self.root()
		snode.insert_child(node, 0)
	    else:
		if snode.leaf_p():
		    snode = snode.parent()
		else: snode.expand()
		snode.append_child(node)
	else: pass
	# scroll the newly added node into view
	self.set_modflag(True)
	self.root_redisplay()
	self.viewer().select_node(node)

    def details(self, event=None):
	node, selection = self._get_selected_node()
	if not node or node.isseparator_p(): return
	if self._details.has_key(id(node)):
	    details = self._details[id(node)]
	    details.show()
	else:
	    details = DetailsDialog(self._frame, node, self)
	    self._details[id(node)] = details

    def show(self, event=None):
	# note that due to a weird Tk `buglet' if you do a deiconify
	# on a newly created toplevel widget, it causes a roundtrip
	# with the X server too early in the widget creation cycle.
	# for those window managers without automatic (random)
	# placement, the user will see a zero-sized widget
	show_p = True
	if not self._dialog:
	    self._dialog = BookmarksDialog(self._frame, self)
	    self._listbox = self._dialog._listbox # TBD: gross
	    viewer = TkListboxViewer(self.root(), self._listbox)
	    self.set_viewer(viewer)
	    viewer.populate()
	    if viewer.count() > 0: viewer.select_node(viewer.node(0))
	    show_p = False
	if show_p: self._dialog.show()

    def hide(self, event=None): self._dialog.hide()
    def quit(self, event=None): sys.exit(0)

    def _insert_at_node(self, node, newnode):
	if node.leaf_p() or not node.expanded_p():
	    parent, sibi, sibs = self._sibi(node)
	    if not parent: return
	    parent.insert_child(newnode, sibi+1)
	else:
	    # Mimic Netscape behavior: when a separator is added to a
	    # header, the node is added as the header's first child.
	    # If the header is collapsed, it is first expanded.
	    node.expand()
	    node.insert_child(newnode, 0)
	self.root_redisplay()
	self.viewer().select_node(newnode)
	self.set_modflag(True)

    def insert_separator(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarkNode()
	newnode.set_separator()
	self._insert_at_node(node, newnode)

    def insert_header(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarkNode('<Category>')
	self._insert_at_node(node, newnode)
	self._details[id(newnode)] = DetailsDialog(self._frame, newnode, self)

    def insert_entry(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarkNode('<Entry>', '  ')
	self._insert_at_node(node, newnode)
	details = self._details[id(newnode)] = \
		  DetailsDialog(self._frame, newnode, self)

    def remove_entry(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	parent = node.parent()
	if not parent: return
	# which node gets selected?
	selection = self.viewer().index(node) - 1
	if selection < 0: selection = 0
	parent.del_child(node)
	self.root_redisplay()
	self.viewer().select_node(self.viewer().node(selection))
	self.set_modflag(True)
	# destroy the details dialog for the node, if it has one
	if self._details.has_key(id(node)):
	    self._details[id(node)].destroy()
	    del self._details[id(node)]

    ## OutlinerController overloads

    def set_aggressive_collapse(self, flag):
	if flag: self.aggressive.set(1)
	else: self.aggressive.set(0)
    def aggressive_collapse_p(self): return self.aggressive.get()

    def collapsable_p(self, node):
	if node == self.root(): return False
	else: return OutlinerController.collapsable_p(self, node)

    ## Commands

    def _cmd(self, method, quiet=False):
	node, selection = self._get_selected_node()
	if node:
	    selected_node = method(node)
	    if not selected_node: selected_node = node
	    self.viewer().select_node(selected_node)
	    self.set_modflag(True, quiet=quiet)

    def shift_left_cmd(self, event=None):  self._cmd(self.shift_left)
    def shift_right_cmd(self, event=None): self._cmd(self.shift_right)
    def shift_up_cmd(self, event=None):    self._cmd(self.shift_up)
    def shift_down_cmd(self, event=None):  self._cmd(self.shift_down)
    def collapse_cmd(self, event=None):
	self._cmd(self.collapse_node, quiet=True)
    def expand_cmd(self, event=None):
	self._cmd(self.expand_node, quiet=True)

    def _prevnext(self, delta):
	node, selection = self._get_selected_node()
	if node:
	    node = self.viewer().node(selection + delta)
	    if node: self.viewer().select_node(node)
    def previous_cmd(self, event=None): self._prevnext(-1)
    def next_cmd(self, event=None): self._prevnext(1)

    def _collapse_children(self, node):
	for child in node.children():
	    if not child.leaf_p() and child.expanded_p():
		child.collapse()
	self.root_redisplay()
	self.viewer().select_node(node)
	self.set_modflag(True, quiet=True)
    def collapse_children(self, event=None):
	node, selection = self._get_selected_node()
	if node: self._collapse_children(node)
    def collapse_top(self, event=None): self._collapse_children(self.root())

    def _expand_children(self, node):
	for child in node.children():
	    if not child.leaf_p() and not child.expanded_p():
		child.expand()
	self.root_redisplay()
	self.viewer().select_node(node)
	self.set_modflag(True, quiet=True)
    def expand_children(self, event=None):
	node, selection = self._get_selected_node()
	if node: self._expand_children(node)
    def expand_top(self, event=None): self._expand_children(self.root())


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
	root = controller.root().clone()
	OutlinerViewer.__init__(self, root)
	self._follow_all_children_p = True

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
	self._app = self._browser.app
	# set up the global controller.  Only one of these in every
	# application
	try: self._controller = self._app.bookmarks_controller
	except AttributeError:
	    self._controller = self._app.bookmarks_controller = \
			       BookmarksController(self._frame, self._app)
	# currently, too difficult to coordinate edits to bookmarks
	# with tear-off menus, so just disable these for now and
	# create the rest of this menu every time the menu is posted
	self._menu.config(tearoff='No', postcommand=self.post)
	# fill in the static part of the menu
	self._menu.add_command(label='Add Current',
			       command=self.add_current,
			       underline=0, accelerator='Alt-A')
	self._browser.root.bind('<Alt-a>', self.add_current)
	self._browser.root.bind('<Alt-A>', self.add_current)
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
	# First make sure the controller has initialized
	self._controller.initialize(active_browser=self._browser)
	viewer = BookmarksMenuViewer(self._controller, self._menu)
	viewer.populate()

    def show(self, event=None):
	# make sure controller is initialized
	self._controller.initialize(active_browser=self._browser)
	self._controller.show()

    def add_current(self, event=None):
	# make sure controller is initialized
	self._controller.initialize(active_browser=self._browser)
	self._controller.add_current()
	self._controller.save()
