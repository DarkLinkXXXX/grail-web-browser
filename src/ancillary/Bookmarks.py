# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

import sys
import os
from Tkinter import *
import FileDialog
from grailutil import *
from Outliner import OutlinerViewer, OutlinerController
import BookmarksParser
import tktools
import formatter
from SGMLParser import SGMLParser
import string
import time


DEFAULT_NETSCAPE_BM_FILE = os.path.join(gethome(), '.netscape-bookmarks.html')
DEFAULT_GRAIL_BM_FILE = os.path.join(getgraildir(), 'grail-bookmarks.html')

BOOKMARKS_FILES = [
    os.path.splitext(DEFAULT_GRAIL_BM_FILE)[0],	# "native" pickled format
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


BMPREFGROUP = 'bookmarks'
ADDLOC_PREF = 'add-location'
COLLAPSE_PREF = 'aggressive-collapse'
INCLUDE_PREF = 'include-in-pulldown'

True = 1
False = None

NEW_AT_BEG = 'file-prepend'
NEW_AT_END = 'file-append'
NEW_AS_CHILD = 'as-child-or-sib'

def username():
    try: name = os.environ['NAME'] + "'s"
    except KeyError:
	try:
	    import pwd
	    name = pwd.getpwuid(os.getuid())[4] + "'s"
	except (ImportError, AttributeError):
	    name = 'Your'
    return name



class FileDialogExtras:
    def __init__(self, frame):
	# create a small subwindow for the extra buttons
	self._controls = Frame(frame, relief=GROOVE, borderwidth=2)
	self._controls.pack(fill=X)
	frame = Frame(self._controls)
	frame.pack(fill=X)
	label = Label(frame, text='Bookmark File Shortcuts:')
	label.pack(side=LEFT, anchor=W)
	grailbtn = Button(frame, text='Grail',
			  command=self.set_for_grail)
	netscapebtn = Button(frame, text='Netscape',
			     command=self.set_for_netscape)
	tktools.unify_button_widths(grailbtn, netscapebtn)
	netscapebtn.pack(side=RIGHT, padx='1m', pady='1m')
	grailbtn.pack(side=RIGHT)
	tktools.unify_button_widths(
	    self.ok_button, self.filter_button, self.cancel_button)

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
    def __init__(self, master, controller, export):
	self._controller = controller
	FileDialog.SaveFileDialog.__init__(self, master, 'Save Bookmarks File')
	FileDialogExtras.__init__(self, self.top)
	self.__create_widgets(export)
	self.set_filetype(
	    export and "html" or
	    controller._app.prefs.Get("bookmarks", "default-save-format"))

    def __create_widgets(self, export):
	self.__filetype = StringVar()
	if not export:
	    frame = Frame(self._controls)
	    frame.pack(fill=X)
	    label = Label(frame, text='File Format:')
	    label.pack(side=LEFT, anchor=W)
	    options = OptionMenu(frame, self.__filetype,
				 "HTML", "Pickle", "Pickle Binary")
	    options["anchor"] = W
	    options["width"] = 13
	    options.pack(side=RIGHT)

    # can't just use regex.casefold since 
    __charmap_out = string.maketrans(string.uppercase + " ",
				     string.lowercase + "-")
    __charmap_in = string.maketrans("-", " ")
    def get_filetype(self):
	return string.translate(self.__filetype.get(), self.__charmap_out)

    def set_filetype(self, filetype):
	dir, oldpat = self.get_filter()
	if filetype[:4] == "html":
	    filetype = "HTML"
	    pat = "*.html"
	else:
	    pat = "*.pkl"
	if pat != oldpat:
	    self.set_filter(dir, pat)
	if filetype != "HTML":
	    filetype = string.capwords(
		string.translate(filetype, self.__charmap_in))
	self.__filetype.set(filetype)


class BookmarksIO:
    def __init__(self, frame, controller):
	self._controller = controller
	self._frame = frame
	self._descriptor = None
	self._filename = None

    def filename(self): return self._filename
    def set_filename(self, filename): self._filename = filename

    def _choose_reader_writer(self, fp):
	format = BookmarksParser.get_format(fp)
	parser, writer = BookmarksParser.get_handlers(format, self._filename)
	# sanity checking
	if not parser or not writer:
	    raise BookmarksParser.BookmarkFormatError(
		self._filename, 'unknown or missing bookmarks file')
	# create the reader
	reader = BookmarksParser.BookmarkReader(parser)
	return (reader, writer)

    def _open_file_for_reading(self, filename):
	reader = writer = None
	try:
	    fp = open(filename, 'r')
	    reader, writer = self._choose_reader_writer(fp)
	except IOError, error:
	    raise BookmarksParser.BookmarkFormatError(self._filename, error)
	return (fp, reader, writer)

    def load(self, usedefault=False):
	if self._filename: filename = self._filename
	else: filename = DEFAULT_GRAIL_BM_FILE
	if not usedefault:
	    loader = BMLoadDialog(self._frame, self._controller)
	    filename = loader.go(filename, '*.html', key="bookmarks")
	# load the file
	root = reader = writer = None
	if filename:
	    fp, reader, writer = self._open_file_for_reading(filename)
	    root = reader.read_file(fp)
	    fp.close()
	    self._filename = filename
	return (root, reader, writer)

    def _save_to_file_with_writer(self, writer, root, filename=None):
	try: os.rename(filename, filename+'.bak')
	except os.error: pass # no file to backup
	fp = open(filename, 'w')
	writer.write_tree(root, fp)

    def save(self, writer, root):
	if not self._filename: self.saveas(writer, root)
	else: self._save_to_file_with_writer(writer, root, self._filename)

    def saveas(self, writer, root, export=0):
	if not self._filename: filename = DEFAULT_GRAIL_BM_FILE
	else: filename = self._filename
	oldformat = writer.get_filetype()
	saver = BMSaveDialog(self._frame, self._controller, export)
	saver.set_filetype(oldformat)
	savefile = saver.go(filename, key="bookmarks")
	if savefile:
	    newformat = saver.get_filetype()
	    if oldformat != newformat:
		writer = BookmarksParser.get_handlers(newformat, '')[1]
	    self._save_to_file_with_writer(writer, root, savefile)
	    self._filename = savefile

class IOErrorDialog:
    def __init__(self, master, where, errmsg):
	msg = 'Bookmark file error encountered %s:' % where
	self._frame = tktools.make_toplevel(master, msg)
	self._frame.protocol('WM_DELETE_WINDOW', self.close)
	label = Label(self._frame, text=msg)
	label.pack()
	errlabel = Label(self._frame, text=errmsg)
	errlabel.pack()
	self.closebtn = Button(self._frame, text="OK", command=self.close)
	self.closebtn.pack()
	self._frame.grab_set()

    def close(self):
	self._frame.grab_release()
	self._frame.destroy()



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
	if index is None: index = END
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
    def __init__(self, master, controller):
	# create the basic controls of the dialog window
	self._frame = tktools.make_toplevel(master, class_='Bookmarks')
	self._frame.title("Grail Bookmarks")
	self._frame.iconname("Bookmarks")
	self._frame.protocol('WM_DELETE_WINDOW', self.cancel_cmd)
	self._controller = controller
	infoframe = Frame(self._frame, name="info")
	infoframe.pack(fill=BOTH)
	self._title = Label(infoframe, text=controller.root().title(),
			    name="title")
	self._title.pack(fill=BOTH)
	self._file = Label(infoframe, text=controller.filename(),
			   name="file")
	self._file.pack(fill=BOTH)
	self._create_menubar()
	self._create_buttonbar()
	self._create_listbox()
	self._create_other_bindings()
	self._frame.focus_set()

    def _create_menubar(self):
	self._menubar = Frame(self._frame, class_="Menubar", name="menubar")
	self._menubar.pack(fill=X)
	#
	# file menu
	#
	filebtn = Menubutton(self._menubar, name="file")
	filebtn.pack(side=LEFT)
	filemenu = Menu(filebtn, name="menu")
	filemenu.add_command(label="Load...",
			     command=self.load,
			     underline=0, accelerator="Alt-L")
	self._frame.bind("<Alt-l>", self.load)
	self._frame.bind("<Alt-L>", self.load)
##	filemenu.add_command(label="Merge...",
##			     command=self._controller.merge,
##			     underline=0, accelerator="Alt-M")
##	self._frame.bind("<Alt-m>", self._controller.merge)
##	# Why can't I bind <Alt-M> here???!!!  I get a TclError...
## 	# The "M" is short for the "Meta-" modifier.
##	self._frame.bind("<Alt-Shift-m>", self._controller.merge)
	filemenu.add_command(label="Save",
			     command=self._controller.save,
			     underline=0, accelerator="Alt-S")
	self._frame.bind("<Alt-s>", self._controller.save)
	self._frame.bind("<Alt-S>", self._controller.save)
	filemenu.add_command(label="Save As...",
			     command=self._controller.saveas)
	filemenu.add_command(label="Export...",
			     command=self._controller.export)
	filemenu.add_command(label="Title...",
			     command=self._controller.title_dialog,
			     underline=0, accelerator="Alt-T")
	self._frame.bind("<Alt-t>", self._controller.title_dialog)
	self._frame.bind("<Alt-T>", self._controller.title_dialog)
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
	#
	# item menu
	#
	itembtn = Menubutton(self._menubar, name='item')
	itembtn.pack(side=LEFT)
	itemmenu = Menu(itembtn, name="menu")
	import SearchMenu
	SearchMenu.SearchMenu(itemmenu, self._frame, self._controller)
	itemmenu.add_separator()
	itemmenu.add_command(label="Add Current",
			     command=self._controller.add_current,
			     underline=0, accelerator='Alt-A')
	self._frame.bind("<Alt-a>", self._controller.add_current)
	self._frame.bind("<Alt-A>", self._controller.add_current)
	insertsubmenu = Menu(itemmenu, tearoff='No')
	insertsubmenu.add_command(label='Insert Separator',
				  command=self._controller.insert_separator,
				  underline=7, accelerator='S')
	self._frame.bind('s', self._controller.insert_separator)
	self._frame.bind('S', self._controller.insert_separator)
	insertsubmenu.add_command(label='Insert Header',
				  command=self._controller.insert_header,
				  underline=7, accelerator='H')
	self._frame.bind('h', self._controller.insert_header)
	self._frame.bind('H', self._controller.insert_header)
	insertsubmenu.add_command(label='Insert Link Entry',
				  command=self._controller.insert_entry,
				  underline=10, accelerator='K')
	self._frame.bind('k', self._controller.insert_entry)
	self._frame.bind('K', self._controller.insert_entry)
	itemmenu.add_cascade(label='Insert', menu=insertsubmenu)
	itemmenu.add_command(label='Remove Entry',
			     command=self._controller.remove_entry,
			     accelerator='X')
	self._frame.bind('x', self._controller.remove_entry)
	self._frame.bind('X', self._controller.remove_entry)
	itemmenu.add_separator()
	itemmenu.add_command(label="Details...",
			     command=self._controller.details,
			     underline=0, accelerator="Alt-D")
	self._frame.bind("<Alt-d>", self._controller.details)
	self._frame.bind("<Alt-D>", self._controller.details)
	itemmenu.add_command(label="Go To Bookmark",
			     command=self._controller.goto,
			     underline=0, accelerator="G")
	self._frame.bind("g", self._controller.goto)
	self._frame.bind("G", self._controller.goto)
	self._frame.bind("<KeyPress-space>", self._controller.goto)
	itemmenu.add_command(label="Go in New Window",
			     command=self._controller.goto_new)
	itembtn.config(menu=itemmenu)
	#
	# arrange menu
	#
	arrangebtn = Menubutton(self._menubar, name="arrange")
	arrangebtn.pack(side=LEFT)
	arrangemenu = Menu(arrangebtn, name="menu")
	arrangemenu.add_command(label="Expand",
			    command=self._controller.expand_cmd,
			    underline=0, accelerator="E")
	self._frame.bind("e", self._controller.expand_cmd)
	self._frame.bind("E", self._controller.expand_cmd)
##	arrangemenu.add_command(label='Expand All Children',
##			     command=self._controller.expand_children)
##	arrangemenu.add_command(label="Expand Top Level",
##			    command=self._controller.expand_top)
##	arrangemenu.add_command(label="Expand All",
##			    command=self._controller.expand_all)
##	arrangemenu.add_separator()
	arrangemenu.add_command(label="Collapse",
			    command=self._controller.collapse_cmd,
			    underline=0, accelerator="C")
	self._frame.bind("c", self._controller.collapse_cmd)
	self._frame.bind("C", self._controller.collapse_cmd)
##	arrangemenu.add_command(label='Collapse All Children',
##			     command=self._controller.collapse_children)
##	arrangemenu.add_command(label="Collapse Top Level",
##			    command=self._controller.collapse_top)
##	arrangemenu.add_command(label="Collapse All",
##			    command=self._controller.collapse_all)
	arrangemenu.add_separator()
	arrangemenu.add_command(label='Shift Entry Left',
			     command=self._controller.shift_left_cmd,
			     underline=12, accelerator='L')
	self._frame.bind('l', self._controller.shift_left_cmd)
	self._frame.bind('L', self._controller.shift_left_cmd)
	arrangemenu.add_command(label='Shift Entry Right',
			     command=self._controller.shift_right_cmd,
			     underline=12, accelerator='R')
	self._frame.bind('r', self._controller.shift_right_cmd)
	self._frame.bind('R', self._controller.shift_right_cmd)
	arrangemenu.add_command(label='Shift Entry Up',
			     command=self._controller.shift_up_cmd,
			     underline=12, accelerator='U')
	self._frame.bind('u', self._controller.shift_up_cmd)
	self._frame.bind('U', self._controller.shift_up_cmd)
	arrangemenu.add_command(label='Shift Entry Down',
			     command=self._controller.shift_down_cmd,
			     underline=12, accelerator='D')
	self._frame.bind('d', self._controller.shift_down_cmd)
	self._frame.bind('D', self._controller.shift_down_cmd)
	arrangebtn.config(menu=arrangemenu)
	self._frame.bind("<Up>", self._controller.previous_cmd)
	self._frame.bind("p", self._controller.previous_cmd)
	self._frame.bind("P", self._controller.previous_cmd)
	self._frame.bind("<Down>", self._controller.next_cmd)
	self._frame.bind("n", self._controller.next_cmd)
	self._frame.bind("N", self._controller.next_cmd)

    def _create_listbox(self):
	self._listbox, frame = tktools.make_list_box(self._frame,
						     60, 24, 1, 1)
	self._listbox.config(font='fixed')
	# bind keys
	self._listbox.bind('<ButtonPress-2>', self._highlight)
	self._listbox.bind('<Double-Button-1>', self._controller.goto)
	self._listbox.bind('<Double-Button-2>', self._controller.goto_new)
	self._listbox.config(takefocus=0, exportselection=0)

    def _create_buttonbar(self):
	# create the button bars
	btmframe = Frame(self._frame)
	btmframe.pack(side=BOTTOM, fill=BOTH)
	topframe = Frame(self._frame)
	topframe.pack(side=BOTTOM, fill=BOTH)
	# bottom buttonbar buttons
	okbtn = Button(self._frame, name='ok', command=self.okay_cmd)
	okbtn.pack(side=LEFT, in_=btmframe)
	savebtn = Button(self._frame, name='save', command=self.save_cmd)
	savebtn.pack(side=LEFT, in_=btmframe)
	self._frame.bind("<Return>", self.okay_cmd)
	status = Label(self._frame, name="status",
		       textvariable=self._controller.statusmsg)
	status.pack(side=LEFT, expand=1, fill=BOTH, in_=btmframe)
	cancelbtn = Button(self._frame, name='cancel', command=self.cancel_cmd)
	cancelbtn.pack(side=RIGHT, in_=btmframe)
	self._frame.bind('<Alt-w>', self.cancel_cmd)
	self._frame.bind('<Alt-W>', self.cancel_cmd)
	self._frame.bind('<Control-c>', self.cancel_cmd)
	self._frame.bind('<Control-C>', self.cancel_cmd)
	# top buttonbar buttons
	prevbtn = Button(self._frame, name='prev',
			 command=self._controller.previous_cmd)
	nextbtn = Button(self._frame, name='next',
			 command=self._controller.next_cmd)
	prevbtn.pack(side=LEFT, expand=1, fill=BOTH, in_=topframe)
	nextbtn.pack(side=LEFT, expand=1, fill=BOTH, in_=topframe)
	gotobtn = Button(self._frame, name='goto',
			 command=self._controller.goto)
	gotobtn.pack(side=LEFT, expand=1, fill=BOTH, in_=topframe)
	colbtn = Button(self._frame, name='collapse',
			command=self._controller.collapse_cmd)
	expbtn = Button(self._frame, name='expand',
			command=self._controller.expand_cmd)
	colbtn.pack(side=LEFT, expand=1, fill=BOTH, in_=topframe)
	expbtn.pack(side=LEFT, expand=1, fill=BOTH, in_=topframe)

    def _create_other_bindings(self):
	# bindings not associated with menu entries of buttons
	w = self._frame
	w.bind("<Home>", self._controller.shift_to_top_cmd)
	w.bind("<End>", self._controller.shift_to_bottom_cmd)

    def set_modflag(self, flag):
	if flag: text = '<== Changes are unsaved!'
	else: text = ''
	self._controller.statusmsg.set(text)

    def load(self, event=None):
	try:
	    self._controller.load()
	except (IOError, BookmarksParser.BookmarkFormatError), errmsg:
	    IOErrorDialog(self._frame, 'during loading', errmsg)

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
	self._frame.focus_set()

    def save_cmd(self, event=None):
	self._controller.save()
    def okay_cmd(self, event=None):
	self._controller.save()
	self._controller.hide()
    def cancel_cmd(self, event=None):
	self._controller.revert()
	self._controller.hide()

    def hide(self):
	browser = self._controller.get_browser().root.focus_set()
	self._frame.withdraw()

    def visible_p(self):
	return self._frame.state() <> 'withdrawn'

    def set_labels(self, filename, title):
	self._file.config(text=filename)
	self._title.config(text=title)

    def _highlight(self, event):
	self._listbox.select_clear(0, END)
	self._listbox.select_set('@%d,%d' % (event.x, event.y))


class DetailsDialog:
    def __init__(self, master, node, controller):
	self._frame = tktools.make_toplevel(master, class_='BookmarkDetail')
#					    title="Bookmark Details")
	self._frame.protocol('WM_DELETE_WINDOW', self.cancel)
	self._node = node
	self._controller = controller
	fr, top, bottom = tktools.make_double_frame(self._frame)
	self._create_form(top)
	self._create_buttonbar(bottom)
	self._frame.bind('<Return>', self.done)
	self._frame.bind('<Alt-W>', self.cancel)
	self._frame.bind('<Alt-w>', self.cancel)
	self._frame.bind('<Control-c>', self.cancel)
	self._frame.bind('<Control-C>', self.cancel)
	self._form[0][0].focus_set()

    def _create_form(self, top):
	self._form = []
	self._add_field(top, 'Name', 40)
	if self._node.islink_p():
	    self._add_field(top, 'Location', 40)
	    self._add_field(top, 'Last Visited', 40)
	self._added_on = self._add_field(top, 'Added On', 40)
	if self._node is self._controller.root():
	    # This field has no meaning for the root, but still create it to
	    # keep the special case logic for root from getting more complex.
	    self._form[-1][1].forget()
	self._description = self._add_field(top, 'Description', 40, 5)
## 	self._form[2][0].config(relief=GROOVE)
## 	self._form[3][0].config(relief=GROOVE)
	self.revert()

    def _add_field(self, master, label, width, height=1):
	tup = tktools.make_labeled_form_entry(master, label, width, height, 12,
					      takefocus=0)
	self._form.append(tup)
	return tup[0]

    def _create_buttonbar(self, top):
	btnbar = Frame(top)
##	revertbtn = Button(top, name='revert', command=self.revert)
	donebtn = Button(top, name='ok', command=self.done)
	applybtn = Button(top, name='apply', command=self.apply)
	cancelbtn = Button(top, name='cancel', command=self.cancel)
	tktools.unify_button_widths(donebtn, applybtn, cancelbtn)
##	revertbtn.pack(side=LEFT, in_=btnbar)
	donebtn.pack(side=LEFT, in_=btnbar)
	applybtn.pack(side=LEFT, padx='1m', in_=btnbar)
	cancelbtn.pack(side=RIGHT, in_=btnbar)
	btnbar.pack(fill=BOTH)

    def revert(self):
	# first we have to re-enable the read-only fields, otherwise
	# Tk will just ignore our updates.  blech!
	for entry, frame, label in self._form[2:]:
	    if type(entry) is type(()): entry[0].config(state=NORMAL)
	    else: entry.config(state=NORMAL)
	# now empty out the text
	for entry, frame, label in self._form:
	    try:
		entry.delete(0, END)
	    except TclError:
		entry.delete(1.0, END)
	# fill in the entry fields
	node = self._node		# convenience
	entry = self._form[0][0]	# more convenience
	entry.insert(0, node.title())
	entry.select_range(0, END)
	if node.islink_p():
	    self._form[1][0].insert(0, node.uri())
	    self._form[2][0].insert(0, time.ctime(node.last_visited()))
	    self._form[2][0].config(state=DISABLED)
	self._added_on.insert(0, time.ctime(node.add_date()))
	self._added_on.config(state=DISABLED)
	self._description.insert(1.0, node.description())

    def apply(self):
	self._node.set_title(self._form[0][0].get())
	if self._node.islink_p():
	    self._node.set_uri(self._form[1][0].get())
	self._node.set_description(self._form[-1][0].get(1.0, END))
	if self._node is self._controller.root():
	    self._controller.update_title_node()
	else:
	    self._controller.viewer().update_node(self._node)
	    self._controller.viewer().select_node(self._node)
	self._controller.set_modflag(True)

    def cancel(self, event=None):
	self.revert()
	self.hide()

    def done(self, event=None):
	self.apply()
	self.hide()

    def show(self):
	self._frame.deiconify()
	self._frame.tkraise()
	self._form[0][0].focus_set()

    def hide(self):
	# these two calls are order dependent!
	self._controller.focus_on_dialog()
	self._frame.withdraw()

    def destroy(self):
	self._frame.destroy()
	self._controller = self._node = None



class BookmarksController(OutlinerController):
    def __init__(self, app):
	default_root = BookmarksParser.BookmarkNode(username()+" Bookmarks")
	OutlinerController.__init__(self, default_root)
	self._master = app.root
	self._app = app
	self._active = None
	self._iomgr = BookmarksIO(self._master, self)
	self._dialog = None
	self._details = {}
	self._listbox = None
	self._writer = BookmarksParser.GrailBookmarkWriter()
	self._initialized_p = False
	self._menus = []
	self._tkvars = {
	    'aggressive': BooleanVar(),
	    'addcurloc':  StringVar(),
	    'fileformat': StringVar(),
	    'statusmsg': StringVar(),
	    'includepulldown': BooleanVar(),
	    }
	# get preferences and set the values
	self._prefs = prefs = app.prefs
	prefs.AddGroupCallback(BMPREFGROUP, self._notify)
	try:
	    where = prefs.Get(BMPREFGROUP, ADDLOC_PREF)
	    if where not in [NEW_AT_BEG, NEW_AT_END, NEW_AS_CHILD]:
		raise TypeError
	except (TypeError, KeyError):
	    where = NEW_AT_BEG
	self.addcurloc.set(where)
	try:
	    aggressive = prefs.GetBoolean(BMPREFGROUP, COLLAPSE_PREF)
	except (TypeError, KeyError):
	    aggressive = 0
	self.aggressive.set(aggressive and 1 or 0)
	try:
	    includepulldown = prefs.GetBoolean(BMPREFGROUP, INCLUDE_PREF)
	except (TypeError, KeyError):
	    includepulldown = 0
	self.includepulldown.set(includepulldown and 1 or 0)
	# other initializations
	self.fileformat.set('Automatic')
	self.statusmsg.set('')
	self._modflag = False
	app.register_on_exit(self.on_app_exit)

    def _notify(self):
	addcurloc = self._prefs.Get(BMPREFGROUP, ADDLOC_PREF)
	aggressive = self._prefs.GetBoolean(BMPREFGROUP, COLLAPSE_PREF)
	includepulldown = self._prefs.GetBoolean(BMPREFGROUP, INCLUDE_PREF)
	self.addcurloc.set(addcurloc)
	self.aggressive.set(aggressive and 1 or 0)
	self.includepulldown.set(includepulldown and 1 or 0)

    def __getattr__(self, name):
	if self._tkvars.has_key(name): return self._tkvars[name]
	else: raise AttributeError, name

    def add_watched_menu(self, menu):
	self._menus.append(menu)

    def remove_watched_menu(self, menu):
	self._menus.remove(menu)

    def set_browser(self, browser=None):
	self._active = browser

    def get_browser(self):
	if self._active not in self._app.browsers:
	    # there better be at least one browser window open!
	    self._active = self._app.browsers[-1]
	return self._active

    ## coordinate with Application instance

    def on_app_exit(self):
	if self._modflag: self.save(exiting=True)
	self._app.unregister_on_exit(self.on_app_exit)

    ## Modifications updating
    def set_modflag(self, flag, quiet=False):
	if not quiet:
	    if self._dialog:
		self._dialog.set_modflag(flag)
	    for menu in self._menus:
		menu.set_modflag(flag)
	self._modflag = flag

    ## I/O

    def initialize(self):
	if self._initialized_p:
	    return
	# attempt to read each bookmarks file in the BOOKMARKS_FILES
	# list.  Search order is 1) $GRAIL_BOOKMARKS_FILE; 2)
	# $GRAIL_DIR/grail-bookmarks.html; 3) ~/.netscape-bookmarks.html
	root = None
	for file in BOOKMARKS_FILES[:]:
	    self._iomgr.set_filename(file)
	    try:
		root, reader, self._writer = self._iomgr.load(True)
		break
	    except BookmarksParser.BookmarkFormatError:
		pass
	if not root:
	    root = BookmarksParser.BookmarkNode(username()+" Bookmarks")
	    self._writer = BookmarksParser.GrailBookmarkWriter()
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
	self._dialog.set_labels(self._iomgr.filename(), root.title())
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

    def export(self):
	self._iomgr.saveas(self._writer, self._root, export=1)
	self.set_modflag(False)
	self.update_backup()
	if self._dialog:
	    self._dialog.set_labels(self._iomgr.filename(), self._root.title())

    # Other commands

    def set_listbox(self, listbox): self._listbox = listbox
    def set_dialog(self, dialog): self._dialog = dialog
    def filename(self): return self._iomgr.filename()
    def dialog_is_visible_p(self):
	return self._dialog and self._dialog.visible_p()

    def focus_on_dialog(self):
	self._dialog and self._dialog.show()

    def _get_selected_node(self):
	node = selection = None
	try:
	    list = self._listbox.curselection()
	    if len(list) > 0:
		selection = string.atoi(list[0])
		return self.viewer().node(selection), selection
	except AttributeError: pass
	return node, selection

    def toggle_node_expansion(self, node):
	if node.expanded_p(): self.collapse_node(node)
	else: self.expand_node(node)
	self.viewer().select_node(node)
	self.set_modflag(True, quiet=True)

    def goto(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	if node.leaf_p():
	    self.goto_node(node)
	else:
	    self.toggle_node_expansion(node)

    def goto_new(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	if node.leaf_p():
	    from Browser import Browser
	    self.goto_node(node, Browser(self._app.root, self._app))
	else:
	    self.toggle_node_expansion(node)

    def bookmark_goto(self, event=None):
	filename = self._iomgr.filename()
	if filename:
	    self.get_browser().context.load('file:' + filename)

    def goto_node(self, node, browser=None):
	if node and node.leaf_p() and node.uri():
	    node.set_last_visited(int(time.time()))
	    if self._details.has_key(id(node)):
		self._details[id(node)].revert()
	    if browser is None:
		browser = self.get_browser()
	    browser.context.load(node.uri())
	    self.viewer().select_node(node)
	    self.set_modflag(True, quiet=True)

    def add_current(self, event=None):
	# create a new node for the page in the current browser
	browser = self.get_browser()
	title = browser.context.get_title()
	url = browser.context.get_baseurl()
	node = self.add_link(url, title)
	headers = browser.context.get_headers()
	if headers.has_key("last-modified"):
	    modified = headers["last-modified"]
	    if type(modified) is type(''):
		import ht_time
		try:
		    modified = ht_time.parse(modified)
		except:
		    pass
		else:
		    node.set_last_modified(modified)

    def add_link(self, url, title=''):
	# create a new node to represent this addition and then fit it
	# into the tree, updating the listbox
	now = int(time.time())
	title = title or self._app.global_history.lookup_url(url)[0] or url
	node = BookmarksParser.BookmarkNode(title, url, now, now)
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
	return node

    def details(self, event=None):
	node, selection = self._get_selected_node()
	self.show_details(node)

    def show_details(self, node):
	if not node or node.isseparator_p(): return
	if self._details.has_key(id(node)):
	    details = self._details[id(node)]
	    details.show()
	else:
	    details = DetailsDialog(self._master, node, self)
	    self._details[id(node)] = details

    def title_dialog(self, event=None):
	self.show_details(self.root())

    def update_title_node(self):
	self._dialog.set_labels(self._iomgr.filename(), self.root().title())

    def show(self, event=None):
	# note that due to a weird Tk `buglet' if you do a deiconify
	# on a newly created toplevel widget, it causes a roundtrip
	# with the X server too early in the widget creation cycle.
	# for those window managers without automatic (random)
	# placement, the user will see a zero-sized widget
	show_p = True
	if not self._dialog:
	    self._dialog = BookmarksDialog(self._master, self)
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
	newnode = BookmarksParser.BookmarkNode()
	newnode.set_separator()
	self._insert_at_node(node, newnode)

    def insert_header(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarksParser.BookmarkNode('<Category>')
	self._insert_at_node(node, newnode)
	self._details[id(newnode)] = DetailsDialog(self._master, newnode, self)

    def insert_entry(self, event=None):
	node, selection = self._get_selected_node()
	if not node: return
	newnode = BookmarksParser.BookmarkNode('<Entry>', '')
	self._insert_at_node(node, newnode)
	details = self._details[id(newnode)] = \
		  DetailsDialog(self._master, newnode, self)

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

    def shift_to_top_cmd(self, event=None):
	node = self.root()
	if node.children():
	    self.viewer().select_node(node.children()[0])

    def shift_to_bottom_cmd(self, event=None):
	node = self.root()
	while node.children():
	    node = node.children()[-1]
	    if node.leaf_p() or not node.expanded_p():
		break
	if node is not self.root():
	    self.viewer().select_node(node)

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

    # interface for searching

    def search_for_pattern(self, pattern,
			   regex_flag, case_flag, backwards_flag):
	# is case important in a literal match?
	if regex_flag:
	    if case_flag:
		cre = regex.compile(pattern, casefold)
	    else:
		cre = regex.compile(pattern)
	elif not case_flag:
	    pattern = string.lower(pattern)
	# depth-first search for the next (or previous) node
	# containing the pattern.  Handle wrapping.
	sv = OutlinerViewer(self._root,
			    follow_all_children=True,
			    shared_root=True)
	sv.populate()
	# get the index of the listbox's selected node in the search
	# viewer's flat space
	startnode, selection = self._get_selected_node()
	nodei = sv.index(startnode)
	node = None
	while 1:
	    if backwards_flag:
		nodei = nodei - 1
		if nodei < 0:
		    nodei = sv.count() - 1
	    else:
		nodei = nodei + 1
		if nodei == sv.count():
		    nodei = 0
	    node = sv.node(nodei)
##	    print 'checking nodei(%d): %s' % (nodei, node)
	    if not node:
		print 'no node for', nodei
		return None
	    # match can occur in the title, uri string, timestamps, or
	    # description string. get this as one big ol' string
	    text = '%s\n%s\n%s\n%s\n%s\n' % (node.title(), node.uri(),
					     time.ctime(node.add_date()),
					     time.ctime(node.last_visited()),
					     node.description())
	    if not regex_flag and not case_flag:
		text = string.lower(text)
	    # literal match
	    if not regex_flag:
		if string.find(text, pattern) >= 0:
		    break
	    # regex match
	    elif cre.search(text) >= 0:
		break
	    # have we gone round the world without a match?
	    if node == startnode:
		return None
	# we found a matching node. make sure it's visible in the
	# listbox and then select it.
	self.show_node(node)
	self.viewer().select_node(node)
	self.set_modflag(True, quiet=True)
	return 1


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
	if node.isseparator_p():
	    menu.add_separator()
	elif node.leaf_p():
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
	self._viewer = None
	# set up the global controller.  Only one of these in every
	# application
	try:
	    self._controller = self._app.bookmarks_controller
	except AttributeError:
	    self._controller = self._app.bookmarks_controller = \
			       BookmarksController(self._app)
	self._controller.add_watched_menu(self)
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

    def post(self, event=None):
	# delete any old existing bookmark entries
	if not self._viewer:
	    last = self._menu.index(END)
	    if last > 1:
		self._menu.delete(2, END)
	    if self._controller.includepulldown.get():
		self._menu.add_separator()
		# First make sure the controller has initialized
		self._controller.initialize()
		self._controller.set_browser(self._browser)
		self._viewer = BookmarksMenuViewer(self._controller,
						   self._menu)
		self._viewer.populate()

    def show(self, event=None):
	# make sure controller is initialized
	self._controller.initialize()
	self._controller.set_browser(self._browser)
	self._controller.show()

    def add_current(self, event=None):
	# make sure controller is initialized
	self._controller.initialize()
	self._controller.set_browser(self._browser)
	self._controller.add_current()
	# if the dialog is unmapped, then do a save
	if not self._controller.dialog_is_visible_p():
	    self._controller.save()

    def set_modflag(self, flag):
	if flag:
	    self._viewer = None

    def close(self):
	self._controller.remove_watched_menu(self)
