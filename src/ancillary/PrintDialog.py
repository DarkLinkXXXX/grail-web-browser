# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""Print Dialog for Grail Browser.

This displays a dialog allowing the user to control printing of the current
document.  The following printing characteristics can be controlled from the
dialog:

	- the print command (which should take PostScript from stdin
	  or a %s can be placed on the command line where the filename
	  of a file containing the postscript output will be placed)
	- a check box for printing to a file
	- the filename (to receive the PostScript instead)
	- some options for controlling the output
	- an OK button
	- a Cancel button

The last state (print command, check box, filename, options) is saved in
a global settings variable.

When OK is activated, the HTML or text file is read using urllib.urlopen()
and the html2ps.PSWriter class is used to generate the PostScript.

When Cancel is actiavted, the dialog state is still saved.

The document to be printed is checked for its MIME type; if it isn't
text/html but is text/*, text/plain is used as the handler.  If no type
is known at all (possibly a disk file without a recognized extension),
an intermediate dialog is used to inform the user that text/plain will
be assumed, giving the option to cancel.

"""

from Cursors import CURSOR_WAIT
from Tkinter import *
import html2ps
import os
import Reader
import string
import sys
import tktools


def get_scaling_adjustments(w):
    scheight = float(w.winfo_screenheight())
    scwidth = float(w.winfo_screenwidth())
    scheight_mm = float(w.winfo_screenmmheight())
    scwidth_mm = float(w.winfo_screenmmwidth())
    vert_pixels_per_in = scheight / (scheight_mm / 25)
    horiz_pixels_per_in = scwidth / (scwidth_mm / 25)
    result = (72.0 / horiz_pixels_per_in), (72.0 / vert_pixels_per_in)
##     print "scaling adjustments:", result
    return result


class PrintSettings:
    """Store the current preference settings."""

    GROUP = 'printing'
    PRINTCMD = "lpr"			# Default print command

    printcmd = None
    printfile = ""
    fileflag = 0
    imageflag = 0
    greyscaleflag = 0
    underflag = 1
    footnoteflag = 1
    fontsize = 10.0
    leading = 10.7
    papersize = "letter"
    orientation = ""
    margins = None
    strip_blanks = 1
    strict_parsing = 0

    def __init__(self, prefs):
	"""Load settings and register an interest in updates."""
	self.__prefs = prefs
	if prefs:
	    self.update()
	    prefs.AddGroupCallback(self.GROUP, self.update)
	    prefs.AddGroupCallback('parsing-html', self.update)

    def update(self):
	"""Load / reload settings from preferences subsystem."""
	prefs = self.__prefs
	#
	self.imageflag = prefs.GetBoolean(self.GROUP, 'images')
	self.fileflag = prefs.GetBoolean(self.GROUP, 'to-file')
	self.greyscaleflag = prefs.GetBoolean(self.GROUP, 'greyscale')
	self.footnoteflag = prefs.GetBoolean(self.GROUP, 'footnote-anchors')
	self.underflag = prefs.GetBoolean(self.GROUP, 'underline-anchors')
	self.set_fontsize(prefs.Get(self.GROUP, 'font-size'))
	self.papersize = prefs.Get(self.GROUP, 'paper-size')
	self.orientation = prefs.Get(self.GROUP, 'orientation')
	self.strip_blanks = prefs.GetBoolean(
	    self.GROUP, 'skip-leading-blank-lines')
	self.strict_parsing = prefs.GetBoolean('parsing-html', 'strict')
	#
	margins = prefs.Get(self.GROUP, 'margins')
	if margins:
	    margins = tuple(map(string.atoi, string.split(margins)))
	    self.margins = margins
	printcmd = prefs.Get(self.GROUP, 'command')
	if not printcmd:
	    printcmd = self.PRINTCMD
	self.printcmd = printcmd

    def set_fontsize(self, spec):
	"""Set font size and leading based on specification string."""
	self.fontsize, self.leading = html2ps.parse_fontsize(spec)

    def get_fontspec(self):
	if self.fontsize == self.leading:
	    return `self.fontsize`
	return "%s / %s" % (self.fontsize, self.leading)


def PrintDialog(context, url, title):
    try:
	infp = context.app.open_url_simple(url)
    except IOError, msg:
	context.error_dialog(IOError, msg)
	return
    try:
	ctype = infp.info()['content-type']
    except KeyError:
	MaybePrintDialog(context, url, title, infp)
	return

    if ";" in ctype:
	pos = string.index(ctype, ";")
	ctype, ctype_params = string.strip(ctype[:pos]), \
			      string.strip(ctype[pos + 1:])
    types = string.splitfields(ctype, '/')
    if types and types[0] == 'text':
	if types[1] != 'html':
	    ctype = 'text/plain'
    if ctype not in ('text/html', 'text/plain'):
	context.error_dialog("Unprintable document",
			     "This document cannot be printed.")
	return
    RealPrintDialog(context, url, title, infp, ctype)


class MaybePrintDialog:

    UNKNOWN_TYPE_MESSAGE = \
"""No MIME type is known for this
document.  It will be printed as
plain text if you elect to continue."""

    def __init__(self, context, url, title, infp):
	self.__context = context
	self.__url = url
	self.__title = title
	self.__infp = infp
	top = self.__top = tktools.make_toplevel(context.browser.root)
	top.title("Print Action")
	fr, topfr, botfr = tktools.make_double_frame(top)
	Label(topfr, bitmap="warning", foreground='red'
	      ).pack(side=LEFT, fill=Y, padx='2m')
	# font used by the Tk4 dialog.tcl script:
	font = "-Adobe-Times-Medium-R-Normal--*-180-*-*-*-*-*-*"
	try:
	    label = Label(topfr, text=self.UNKNOWN_TYPE_MESSAGE,
			  font=font, justify=LEFT)
	except TclError:
	    # font not found, use one we are sure exists:
	    font = context.browser.viewer.text.tag_cget('h2_b', '-font')
	    label = Label(topfr, text=self.UNKNOWN_TYPE_MESSAGE,
			  font=font, justify=LEFT)
	label.pack(side=RIGHT, fill=BOTH, expand=1, padx='1m')
	b1 = Button(botfr, text="Cancel", command=self.skipit)
	b1.pack(side=RIGHT)
	b2 = Button(botfr, text="Print", command=self.doit)
	b2.pack(side=LEFT)
	tktools.unify_button_widths(b1, b2)
	tktools.set_transient(top, context.browser.root)

    def doit(self, event=None):
	self.__top.destroy()
	RealPrintDialog(self.__context,
			self.__url,
			self.__title,
			self.__infp,
			"text/plain")
	self.__context = None
	self.__infp = None

    def skipit(self, event=None):
	self.__context = None
	self.__top.destroy()
	self.__infp.close()
	self.__infp = None


class RealPrintDialog:

    def __init__(self, context, url, title, infp, ctype):
	self.infp = infp
	self.ctype = ctype
	self.context = context
	self.baseurl = context.get_baseurl()
	self.prefs = context.app.prefs

	global settings
	try:
	    x = settings		# NameError first time
	except NameError:
	    settings = PrintSettings(context.app.prefs)
	self.title = title
	self.master = self.context.root
	import tktools
	self.root = tktools.make_toplevel(self.master,
					  title="Print Dialog",
					  class_="PrintDialog")
	# do this early in case we're debugging:
	self.root.protocol('WM_DELETE_WINDOW', self.cancel_command)
	self.root.bind("<Alt-w>", self.cancel_event)
	self.root.bind("<Alt-W>", self.cancel_event)
	self.cursor_widgets = [self.root]
	#
	adjust = get_scaling_adjustments(self.root)
	html2ps.PIXEL_SIZE_ADJUST_HORIZ = adjust[0]
	html2ps.PIXEL_SIZE_ADJUST_VERT = adjust[1]

	fr, top, botframe = tktools.make_double_frame(self.root)

	#  Print to file controls:
	generalfr = tktools.make_group_frame(
	    top, "general", "General options:", fill=X)

	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    generalfr, "Print command:")
	self.cmd_entry.insert(END, settings.printcmd)
	self.add_entry(self.cmd_entry)
	self.printtofile = IntVar(self.root)
	self.printtofile.set(settings.fileflag)
	fr = Frame(generalfr)
	fr.pack(fill=X)
	self.file_check = Checkbutton(fr, text = "Print to file:",
				      command = self.check_command,
				      variable = self.printtofile)
	self.file_check.pack(side=LEFT)
	self.file_entry = Entry(fr)
	self.file_entry.pack(side=RIGHT, fill=X)
	self.file_entry.insert(END, settings.printfile)
	self.add_entry(self.file_entry)

	# page orientation
	Frame(generalfr, height=2).pack()
	fr = Frame(generalfr)
	fr.pack(fill=X)
	self.orientation = StringVar(top)
	self.orientation.set(string.capitalize(settings.orientation))
	opts = html2ps.paper_rotations.keys()
	opts.sort()
	opts = tuple(map(string.capitalize, opts))
	Label(fr, text="Orientation: ", width=13, anchor=E).pack(side=LEFT)
	Frame(fr, width=3).pack(side=LEFT)
	menu = apply(OptionMenu, (fr, self.orientation) + opts)
	width = reduce(max, map(len, opts), 6)
	menu.config(anchor=W, highlightthickness=0, width=width)
	menu.pack(expand=1, fill=NONE, anchor=W, side=LEFT)
	Frame(generalfr, height=2).pack()
	# font size
	fr = Frame(generalfr)
	fr.pack(fill=X)
	Label(fr, text="Font size: ", width=13, anchor=E).pack(side=LEFT)
	Frame(fr, width=3).pack(side=LEFT)
	e = self.fontsize = Entry(fr, width=12)
	e.insert(END, settings.get_fontspec())
	e.pack(side=LEFT)
	self.add_entry(e)

	Frame(top, height=8).pack()
	if self.ctype == "text/html":
	    htmlfr = tktools.make_group_frame(
		top, "html", "HTML options:", fill=X)
	    #  Image printing controls:
	    self.imgchecked = self.new_checkbox(
		htmlfr, "Print images", settings.imageflag)
	    self.greychecked = self.new_checkbox(
		htmlfr, "Reduce images to greyscale", settings.greyscaleflag)
	    #  Anchor-handling selections:
	    self.footnotechecked = self.new_checkbox(
		htmlfr, "Footnotes for anchors", settings.footnoteflag)
	    self.underchecked = self.new_checkbox(
		htmlfr, "Underline anchors", settings.underflag)
	else:
	    textfr = tktools.make_group_frame(
		top, "textoptions", "Text options:", fill=X)
	    #  The titleentry widget is used to set the title for text/plain
	    #  documents; the title is printed in the page headers.
	    self.titleentry, dummyframe = tktools.make_form_entry(
		textfr, "Title:")
	    self.add_entry(self.titleentry)
	    Frame(textfr, height=4).pack()
	    self.strip_blanks = self.new_checkbox(
		textfr, "Strip leading blank lines", settings.strip_blanks)

	#  Command buttons:
	ok_button = Button(botframe, text="OK",
			   command=self.ok_command)
	ok_button.pack(side=LEFT)
	cancel_button = Button(botframe, text="Cancel",
			       command=self.cancel_command)
	cancel_button.pack(side=RIGHT)
	tktools.unify_button_widths(ok_button, cancel_button)

	tktools.set_transient(self.root, self.master)
	self.check_command()

    def new_checkbox(self, parent, description, value):
	var = BooleanVar(parent)
	var.set(value)
	Checkbutton(parent, text=description, variable=var, anchor=W
		    ).pack(anchor=W, fill=X)
	return var

    def add_entry(self, entry):
	self.cursor_widgets.append(entry)
	entry.bind("<Return>", self.return_event)

    def return_event(self, event):
	self.ok_command()

    def check_command(self):
	if self.printtofile.get():
	    self.file_entry['state'] = NORMAL
	    self.cmd_entry['state'] = DISABLED
	    self.file_entry.focus_set()
	else:
	    self.file_entry['state'] = DISABLED
	    self.cmd_entry['state'] = NORMAL
	    self.cmd_entry.focus_set()

    def ok_command(self):
	if self.printtofile.get():
	    filename = self.file_entry.get()
	    if not filename:
		self.context.error_dialog("No file",
					  "Please enter a filename")
		return
	    try:
		fp = open(filename, "w")
	    except IOError, msg:
		self.context.error_dialog(IOError, str(msg))
		return
	else:
	    cmd = self.cmd_entry.get()
	    if not cmd:
		self.context.error_dialog("No command",
					  "Please enter a print command")
		return
	    try:
		if string.find(cmd, '%s') != -1:
		    import tempfile
		    tempname = tempfile.mktemp()
		    fp = open(tempname, 'w')
		else:
		    fp = os.popen(cmd, "w")
	    except IOError, msg:
		self.context.error_dialog(IOError, str(msg))
		return
	for e in self.cursor_widgets:
	    e['cursor'] = CURSOR_WAIT
	self.root.update_idletasks()
	try:
	    self.print_to_fp(fp)
	except:
	    # don't want a try/finally since we don't need this to
	    # execute unless we received an error
	    for e in self.cursor_widgets: e['cursor'] = ''
	    raise sys.exc_type, sys.exc_value, sys.exc_traceback
	sts = fp.close()
	if not sts:
	    try:
		cmd_parts = string.splitfields(cmd, '%s')
		cmd = string.joinfields(cmd_parts, tempname)
		sts = os.system(cmd)
		os.unlink(tempname)
	    except NameError:		# expected on tempname except on NT
		pass
	if sts:
	    self.context.error_dialog("Exit",
				      "Print command exit status %s" % `sts`)
	self.root.destroy()

    def cancel_event(self, event):
	self.cancel_command()

    def cancel_command(self):
	self.update_settings()
	self.root.destroy()

    def print_to_fp(self, fp):
	# do the printing
	self.update_settings()
	html2ps.USERHEADER_FILENAME = self.prefs.Get(
	    settings.GROUP, 'user-header')
	paper = html2ps.PaperInfo(settings.papersize)
	paper.rotate(settings.orientation)
	if settings.margins:
	    paper.set_margins(settings.margins)
	w = html2ps.PSWriter(fp, self.title, self.baseurl, paper=paper,
			     fontsize=settings.fontsize,
			     leading=settings.leading)
	if self.ctype == 'text/html':
	    imgloader = (settings.imageflag and html2ps.image_loader) or None
	    p = html2ps.PrintingHTMLParser(
		w, baseurl=self.baseurl, image_loader=imgloader,
		greyscale=settings.greyscaleflag,
		underline_anchors=settings.underflag,
		strict=settings.strict_parsing)
	    if not settings.footnoteflag:
		p.add_anchor_transform(html2ps.disallow_anchor_footnotes)
	    else:
		p.add_anchor_transform(
		    html2ps.disallow_self_reference(self.baseurl))
	    p.iconpath = self.context.app.iconpath
	else:
	    p = PrintingTextParser(w, title=self.titleentry.get(),
				   strip_blanks=settings.strip_blanks)
	p.feed(self.infp.read())
	self.infp.close()
	p.close()
	w.close()

    def update_settings(self):
	settings.printcmd = self.cmd_entry.get()
	settings.printfile = self.file_entry.get()
	settings.fileflag = self.printtofile.get()
	settings.set_fontsize(self.fontsize.get())
	settings.orientation = string.lower(self.orientation.get())
	if self.ctype == "text/html":
	    settings.footnoteflag = self.footnotechecked.get()
	    settings.greyscaleflag = self.greychecked.get()
	    settings.imageflag = self.imgchecked.get()
	    settings.underflag = self.underchecked.get()
	else:
	    settings.strip_blanks = self.strip_blanks.get()


class PrintingTextParser(Reader.TextParser):
    __buffer = ''

    def __init__(self, writer, strip_blanks=0, title=''):
	self.__strip_blanks = strip_blanks
	writer.ps.set_title(title)
	writer.ps.prune_titles()
	Reader.TextParser.__init__(self, writer)

    def close(self):
	self.write_page(self.__buffer)
	self.__buffer = ''
	Reader.TextParser.close(self)

    def feed(self, data):
	data = self.__buffer + data
	self.__buffer = ''
	strings = string.splitfields(data, "\f")
	if strings:
	    for s in strings[:-1]:
		self.write_page(s)
	    self.__buffer = strings[-1]

    __first = 1
    def write_page(self, data):
	data = string.rstrip(data)
	if self.__strip_blanks:
	    data = self.strip_blank_lines(data)
	    # discard blank pages:
	    if not data:
		return
	if self.__first:
	    self.__first = 0
	else:
	    self.viewer.ps.close_line()
	    self.viewer.ps.push_page_break()
	self.viewer.send_literal_data(data)

    def strip_blank_lines(self, data):
	lines = map(string.rstrip, string.splitfields(data, "\n"))
	while lines:
	    if string.strip(lines[0]) == "":
		del lines[0]
	    else:
		break
	return string.joinfields(lines, "\n")
