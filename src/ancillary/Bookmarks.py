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


def username():
    try: name = os.environ['NAME']
    except KeyError:
	import pwd
	import posix
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

    def _choose_reader_writer(self, fp):
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
	    raise BookmarkFormatError, \
		  'unknown bookmark file format for file %s' % filename
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
	fp = open(filename, 'w')
	writer.write_tree(root, fp)

    def save(self, writer, root):
	if not self._filename:
	    self._filename = DEFAULT_GRAIL_BM_FILE
	    self.saveas(writer, root)
	else:
	    self._save_to_file_with_writer(writer, root, self._filename)

    def saveas(self, writer, root):
	saver = BMSaveDialog(self._frame, self._controller)
	savefile = saver.go(self._filename, '*.html')
	if savefile:
	    self._save_to_file_with_writer(writer, root, savefile)
	    self._filename = savefile

class IOErrorDialog:
    def __init__(self, master, where, errmsg):
	msg = 'Bookmark file error encountered during %s:' % where
	self._frame = Toplevel(master)
	self._frame.title(msg)
	label = Label(self._frame, text=msg)
	label.pack()
	errlabel = Label(self._frame, text=errmsg)
	errlabel.pack()
	self.closebtn = Button(self._frame, text="Ok", command=self.close)
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

    def populate(self):
	# we don't want the root node to show up
	if not self._root: return
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


class BookmarksDialog:
    def __init__(self, frame, controller):
	# create the basic controls of the dialog window
	self._frame = Toplevel(frame)
	self._controller = controller
	infoframe = Frame(self._frame, relief=GROOVE, borderwidth=2)
	infoframe.pack(fill=BOTH)
	self._title = Label(infoframe, text=controller.root().title())
	self._title.pack(fill=BOTH)
	self._file = Label(infoframe, text=controller.filename())
	self._file.pack(fill=BOTH)
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
	editmenu.add_command(label="Add Current",
			     command=self._controller.add_current,
			     underline=0, accelerator='Alt-A')
	self._frame.bind("<Alt-a>", self._controller.add_current)
	self._frame.bind("<Alt-A>", self._controller.add_current)
	editmenu.add_separator()
	editmenu.add_command(label="Expand",
			    command=self._controller.expand,
			    accelerator="Alt-E")
	self._frame.bind("<Alt-e>", self._controller.expand)
	self._frame.bind("<Alt-E>", self._controller.expand)
	editmenu.add_command(label='Expand All Children',
			     command=self._controller.expand_children)
	editmenu.add_command(label="Expand Top Level",
			    command=self._controller.expand_top)
#	editmenu.add_command(label="Expand All",
#			    command=self._controller.expand_all)
	editmenu.add_separator()
	editmenu.add_command(label="Collapse",
			    command=self._controller.collapse,
			    accelerator="Alt-C")
	self._frame.bind("<Alt-c>", self._controller.collapse)
	self._frame.bind("<Alt-C>", self._controller.collapse)
	editmenu.add_command(label='Collapse All Children',
			     command=self._controller.collapse_children)
	editmenu.add_command(label="Collapse Top Level",
			    command=self._controller.collapse_top)
#	editmenu.add_command(label="Collapse All",
#			    command=self._controller.collapse_all)
	editmenu.add_separator()
	editmenu.add_command(label='Insert Separator',
			     command=self._controller.insert_separator)
	editmenu.add_command(label='Insert Header',
			     command=self._controller.insert_header)
	editmenu.add_command(label='Insert Entry',
			     command=self._controller.insert_entry)
	editmenu.add_command(label='Remove Entry',
			     command=self._controller.remove_entry)
	editmenu.add_command(label='Shift Entry Left',
			     command=self._controller.shift_left)
	editmenu.add_command(label='Shift Entry Right',
			     command=self._controller.shift_right)
	editmenu.add_command(label='Shift Entry Up',
			     command=self._controller.shift_up)
	editmenu.add_command(label='Shift Entry Down',
			     command=self._controller.shift_down)
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

    def load(self, event=None):
	try:
	    self._controller.load()
	except (IOError, BookmarkFormatError), errmsg:
	    IOErrorDialog(self._frame, 'loading', errmsg)

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
	self._listbox.focus_set()

    def hide(self): self._frame.withdraw()

    def set_labels(self, filename, title):
	self._file.config(text=filename)
	self._title.config(text=title)


class DetailsDialog:
    def __init__(self, frame, node, controller):
	self._frame = frame
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

    def done(self, event=None):
	self.apply()
	self.hide()

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()

    def hide(self): self._frame.withdraw()



class BookmarksController:
    def __init__(self, frame, browser):
	self._frame = frame
	self._browser = browser
	self._root = None
	self._viewer = None
	self._iomgr = BookmarksIO(frame, self)
	self._dialog = None
	self._details = {}
	self._listbox = None
	self._writer = GrailBookmarkWriter()
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

    def root(self): return self._root
    def select(self, event=None): pass
    def filename(self): return self._iomgr.filename()

    def goto(self, event=None):
	node, selection = self._get_selected_node()
	self.goto_node(node)
    def bookmark_goto(self, event=None):
	filename = self._iomgr.filename()
	if filename: self._browser.load('file:' + filename)
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
    def collapse_children(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	for child in node.children():
	    if not child.leaf_p() and child.expanded_p():
		self._collapse_node(child)
    def collapse_top(self, event=None):
	for child in self._root.children():
	    self._collapse_node(child)
    def collapse_all(self, event=None):
	pass
    def expand(self, event=None):
	node, selection = self._get_selected_node()
	# can't expand leaves or already expanded nodes
	if node and not node.leaf_p() and not node.expanded_p():
	    self._expand_node(node)
    def expand_children(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	for child in node.children():
	    if not child.leaf_p() and not child.expanded_p():
		self._expand_node(child)
    def expand_top(self, event=None):
	for child in self._root.children():
	    self._expand_node(child)
    def expand_all(self, event=None):
	pass

    def previous(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection > 0:
	    self._viewer.select_node(selection-1)

    def next(self, event=None):
	node, selection = self._get_selected_node()
	if node and selection < self._viewer.count()-1:
	    self._viewer.select_node(selection+1)

    def load_default(self):
	try: self._root, reader, self._writer = self._iomgr.load(True)
	except BookmarkFormatError:
	    self._root = BookmarkNode(username()+"'s Bookmarks")

    def load(self):
	self._root, reader, self._writer = self._iomgr.load()
	self._dialog.set_labels(self._iomgr.filename(), self._root.title())
	if self._listbox:
	    self._listbox.delete(0, 'end')
	    self._viewer = None
	self.show()

    def merge(self, event=None): pass
    def save(self, event=None):
	self._iomgr.save(self._writer, self._root)
	self._dialog.set_labels(self._iomgr.filename(), self._root.title())

    def saveas(self, event=None):
	self._iomgr.saveas(self._writer, self._root)
	self._dialog.set_labels(self._iomgr.filename(), self._root.title())

    def add_current(self, event=None):
	# create a new node to represent this addition and then fit it
	# into the tree, updating the listbox
	see = not not self._viewer
	now = int(time.time())
	node = BookmarkNode(self._browser.title,
			    self._browser.url,
			    now, now)
	addlocation = self.addcurloc.get()
	if addlocation == 1:
	    # append this to the end of the list, which translates to:
	    # add this node to the end of root's child list.
	    self._root.append_child(node)
	    if self._viewer:
		lastnode = self._viewer.count()
		self._viewer.insert_nodes(lastnode, [node], True)
	elif addlocation == 2:
	    # prepend the node to the front of the list, which
	    # translates to: add this node to the beginning of root's
	    # child list.
	    self._root.insert_child(node, 0)
	    if self._viewer:
		self._viewer.insert_nodes(0, [node], True)
	elif addlocation == 3 and self._viewer:
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
	else: pass
	# scroll the newly added node into view
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
	# note that due to a weird Tk `buglet' if you do a deiconify
	# on a newly created toplevel widget, it causes a roundtrip
	# with the X server too early in the widget creation cycle.
	# for those window managers without automatic (random)
	# placement, the user will see a zero-sized widget
	show_p = True
	if not self._root:
	    self._root = BookmarkNode(username()+"'s Bookmarks")
	if not self._dialog:
	    self._dialog = BookmarksDialog(self._frame, self)
	    self._listbox = self._dialog._listbox # TBD: gross
	    show_p = False
	if not self._viewer:
	    self._viewer = TkListboxViewer(self._root, self._listbox)
	    self._viewer.populate()
	if show_p: self._dialog.show()

    def hide(self, event=None): self._dialog.hide()
    def quit(self, event=None): sys.exit(0)

    def insert_separator(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarkNode()
	newnode.set_separator()
	if node.leaf_p():
	    parent = node.parent()
	    children = parent.children()
	    nodei = children.index(node)
	    if nodei == len(children): parent.append_child(newnode)
	    else: parent.insert_child(newnode, nodei+1)
	else:
	    # Mimic Netscape behavior: when a separator is added to a
	    # header, the node is added as the header's first child.
	    # If the header is collapsed, it is first expanded.
	    if not node.expanded_p(): self._expand_node(node)
	    parent = node.parent()
	    parent.insert_child(newnode, 0)
	if self._viewer:
	    self._viewer.insert_nodes(node.index(), [newnode])

    def insert_header(self, event=None): pass
    def insert_entry(self, event=None): pass
    def remove_entry(self, event=None): pass
    def shift_left(self, event=None): pass
    def shift_right(self, event=None): pass
    def shift_up(self, event=None): pass
    def shift_down(self, event=None): pass



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
	self._follow_all_children_p = True

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
	# get the root of the current tree from the controller,
	# telling it to load the tree if necessary.
	if not self._controller.root():
	    try: self._controller.load_default()
	    except BookmarkFormatError: pass
	if self._controller.root():
	    viewer = BookmarksMenuViewer(self._controller, self._menu)
	    viewer.populate()

    def show(self, event=None):
	if not self._controller.root(): self._controller.load_default()
	self._controller.show()

    def add_current(self, event=None):
	if not self._controller.root(): self._controller.load_default()
	self._controller.add_current()
