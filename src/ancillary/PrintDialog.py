"""Print Dialog for Grail Browser.

This displays a really basic modal dialog, containing:

	- the print command (which should take PostScript from stdin
	  or a %s can be placed on the command line where the filename
	  of a file containing the postscript output will be placed)
	- a check box for printing to a file
	- the filename (to receive the PostScript instead)
	- some options for controlling the output
	- an OK button
	- a Cancel button

The last state (print command, check box, filename, options) is saved in
globals  variables.

The dialog is modal by virtue of grabbing the focus and running
the Tk mainloop recursively.

When OK is activated, the HTML file is read using urllib.urlopen() and
the html2ps.PSWriter class is used to generate the PostScript.

When Cancel is actiavted, the dialog state is still saved.

The document to be printed is checked for its MIME type; if it isn't
text/html but is text/*, text/plain is used as the handler.  If no type
is known at all (possibly a disk file without a recognized extension),
an intermediate dialog is used to inform the user that text/plain will
be assumed, giving the option to cancel.

"""

from Cursors import CURSOR_WAIT
from Tkinter import *
import os
import Reader
import string
import tktools

PRINT_PREFGROUP = 'printing'
PRINTCMD = "lpr"			# Default print command

# Global variables tracking the last contents of the dialog box.
# If printcmd is None, these need to be inited from preferences.
printcmd = None
printfile = ""
fileflag = 0
imageflag = 0
greyscaleflag = 0
underflag = 1
footnoteflag = 1
fontsize = 10.0
leading = 10.7
papersize = ""
orientation = ""

global_prefs = None


def update_options(prefs=None):
    """Load/reload preferences.
    """
    global printcmd, printfile, fileflag, imageflag, greyscaleflag
    global underflag, footnoteflag, global_prefs, leading, fontsize
    global papersize, orientation
    from html2ps import parse_fontsize
    #
    prefs = prefs or global_prefs
    if prefs:
	global_prefs = prefs
    else:
	return
    imageflag = prefs.GetBoolean(PRINT_PREFGROUP, 'images')
    fileflag = prefs.GetBoolean(PRINT_PREFGROUP, 'to-file')
    greyscaleflag = prefs.GetBoolean(PRINT_PREFGROUP, 'greyscale')
    printcmd = prefs.Get(PRINT_PREFGROUP, 'command')
    footnoteflag = prefs.GetBoolean(PRINT_PREFGROUP, 'footnote-anchors')
    underflag = prefs.GetBoolean(PRINT_PREFGROUP, 'underline-anchors')
    fontsize, leading = parse_fontsize(
	prefs.Get(PRINT_PREFGROUP, 'font-size'))
    papersize = prefs.Get(PRINT_PREFGROUP, 'paper-size')
    orientation = prefs.Get(PRINT_PREFGROUP, 'orientation')
    if not printcmd:
	printcmd = PRINTCMD


def PrintDialog(context, url, title):
    try:
	infp = context.app.open_url_simple(url)
    except IOError, msg:
	context.error_dialog(IOError, msg)
	return
    import html2ps
    if not html2ps.standard_header_template:
	context.app.error_dialog("Missing file",
				 "header.ps missing from the source directory")
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
	top = self.__top = Toplevel(context.browser.root)
	top.title("Print Action")
	fr, topfr, botfr = tktools.make_double_frame(top)
	Label(topfr, bitmap="warning", foreground='darkblue'
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

	global printcmd
	self.context = context
	self.baseurl = context.get_baseurl()
	prefs = context.app.prefs
	if not prefs:
	    printcmd = PRINTCMD
	elif printcmd is None:
	    # first time only
	    update_options(prefs)
	    prefs.AddGroupCallback(PRINT_PREFGROUP, update_options)
	self.url = url
	self.title = title
	self.master = self.context.root
	import tktools
	self.root = tktools.make_toplevel(self.master,
					  title="Print Dialog",
					  class_="PrintDialog")
	self.root.iconname("Print Dialog")
	# do this early in case we're debugging:
	self.root.protocol('WM_DELETE_WINDOW', self.cancel_command)
	self.root.bind("<Alt-w>", self.cancel_event)
	self.root.bind("<Alt-W>", self.cancel_event)

	fr, top, botframe = tktools.make_double_frame(self.root)

	#  Print to file controls:
	generalfr = tktools.make_group_frame(
	    top, "general", "General options:", fill=X)

	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    generalfr, "Print command:")
	self.cmd_entry.insert(END, printcmd)
	self.printtofile = IntVar(self.root)
	self.printtofile.set(fileflag)
	fr = Frame(generalfr)
	fr.pack(fill=X)
	self.file_check = Checkbutton(fr, text = "Print to file:",
				      command = self.check_command,
				      variable = self.printtofile)
	self.file_check.pack(side=LEFT)
	self.file_entry = Entry(fr)
	self.file_entry.pack(side=RIGHT, fill=X)
	self.file_entry.insert(END, printfile)

	# page orientation
	Frame(generalfr, height=2).pack()
	fr = Frame(generalfr)
	fr.pack(fill=X)
	self.orientation = StringVar(top)
	self.orientation.set(string.capitalize(orientation))
	import html2ps
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
	self.fontsize = StringVar(top)
	if fontsize == leading:
	    self.fontsize.set(`fontsize`)
	else:
	    self.fontsize.set("%s / %s" % (fontsize, leading))
	Label(fr, text="Font size: ", width=13, anchor=E).pack(side=LEFT)
	Frame(fr, width=3).pack(side=LEFT)
	e = Entry(fr, textvariable=self.fontsize, width=12)
	e.pack(side=LEFT)
	e.bind('<Return>', self.return_event)

	if self.ctype == "text/html":
	    Frame(top, height=8).pack()
	htmlfr = tktools.make_group_frame(
	    top, "html", "HTML options:", fill=X)

	#  Image printing controls:
	self.imgchecked = self.add_html_checkbox(
	    htmlfr, "Print images", imageflag)
	self.greychecked = self.add_html_checkbox(
	    htmlfr, "Reduce images to greyscale", greyscaleflag)

	#  Anchor-handling selections:
	self.footnotechecked = self.add_html_checkbox(
	    htmlfr, "Footnotes for anchors", footnoteflag)
	self.underchecked = self.add_html_checkbox(
	    htmlfr, "Underline anchors", underflag)

	if self.ctype != "text/html":
	    htmlfr.forget()

	#  Command buttons:
	ok_button = Button(botframe, text="OK",
			   command=self.ok_command)
	ok_button.pack(side=LEFT)
	cancel_button = Button(botframe, text="Cancel",
			       command=self.cancel_command)
	cancel_button.pack(side=RIGHT)
	tktools.unify_button_widths(ok_button, cancel_button)

	self.cmd_entry.bind('<Return>', self.return_event)
	self.file_entry.bind('<Return>', self.return_event)

	tktools.set_transient(self.root, self.master)
	self.check_command()

    def add_html_checkbox(self, root, description, value):
	var = BooleanVar(root)
	var.set(value)
	if self.ctype == "text/html":
	    Checkbutton(root, text=description, variable=var, anchor=W
			).pack(anchor=W, fill=X)
	return var

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
	self.root['cursor'] = CURSOR_WAIT
	self.cmd_entry['cursor'] = CURSOR_WAIT
	self.file_entry['cursor'] = CURSOR_WAIT
	self.root.update_idletasks()
	self.print_to_fp(fp)
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
	self.goaway()

    def cancel_event(self, event):
	self.cancel_command()

    def cancel_command(self):
	self.goaway()

    def print_to_fp(self, fp):
	# do the printing
	global fontsize, leading, orientation
	from html2ps import PSWriter, PrintingHTMLParser, PaperInfo
	from html2ps import disallow_anchor_footnotes, parse_fontsize

	paper = None
	orientation = string.lower(self.orientation.get())
	if orientation or papersize:
	    paper = PaperInfo(papersize or "letter")
	    if orientation:
		paper.rotate(orientation)
	fontsize, leading = parse_fontsize(self.fontsize.get())
	w = PSWriter(fp, self.title, self.url,
		     fontsize=fontsize, leading=leading, paper=paper)
	if self.ctype == 'text/html':
	    imgloader = (self.imgchecked.get() and self.image_loader) or None
	    grey = self.greychecked.get()
	    p = PrintingHTMLParser(w, baseurl=self.baseurl,
				   image_loader=imgloader, greyscale=grey,
				   underline_anchors=self.underchecked.get())
	    if not self.footnotechecked.get():
		p.add_anchor_transform(disallow_anchor_footnotes)
	    p.iconpath = self.context.app.iconpath
	else:
	    p = PrintingTextParser(w)
	p.feed(self.infp.read())
	self.infp.close()
	p.close()
	w.close()

    def goaway(self):
	global printcmd, printfile, fileflag, imageflag, greyscaleflag
	global underflag, footnoteflag, leading, fontsize, papersize
	global orientation
	from html2ps import parse_fontsize
	#
	printcmd = self.cmd_entry.get()
	printfile = self.file_entry.get()
	fileflag = self.printtofile.get()
	footnoteflag = self.footnotechecked.get()
	greyscaleflag = self.greychecked.get()
	imageflag = self.imgchecked.get()
	underflag = self.underchecked.get()
	fontsize, leading = parse_fontsize(self.fontsize.get())
	orientation = self.orientation.get()
	self.root.destroy()

    def image_loader(self, url):
	"""Image loader for the PrintingHTMLParser instance."""
	#  This needs a lot of work for efficiency and connectivity
	#  with the rest of grail.
	from urllib import urlopen
	from tempfile import mktemp
	try:
	    imgfp = urlopen(url)
	except IOError, msg:
	    return None
	data = imgfp.read()
	return data


class PrintingTextParser(Reader.TextParser):
    def feed(self, data):
	strings = string.splitfields(data, "\f")
	if strings:
	    self.viewer.send_literal_data(strings[0])
	    for s in strings[1:]:
		self.viewer.ps.push_page_break()
		self.viewer.send_literal_data(s)
