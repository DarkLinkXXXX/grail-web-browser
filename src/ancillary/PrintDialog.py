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
leading = 0.7
fontsize = None

global_prefs = None


def update_options(prefs=None):
    """Load/reload preferences.
    """
    global printcmd, printfile, fileflag, imageflag, greyscaleflag
    global underflag, footnoteflag, global_prefs, leading, fontsize
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
    leading = prefs.GetFloat(PRINT_PREFGROUP, 'leading')
    fontsize = prefs.GetFloat(PRINT_PREFGROUP, 'base-font-size')
    if not printcmd:
	printcmd = PRINTCMD


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
	fr, top, botframe = tktools.make_double_frame(self.root)
	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    top, "Print command:")
	self.cmd_entry.insert(END, printcmd)

	#  Print to file controls:
	self.midframe = Frame(top)
	self.midframe.pack(side=TOP, fill=X)

	self.checked = IntVar(self.root)
	self.checked.set(fileflag)
	self.file_check = Checkbutton(self.midframe,
				      text = "Print to file:",
				      command = self.check_command,
				      variable = self.checked)
	self.file_check.pack(side=LEFT)
	self.file_entry = Entry(self.midframe)
	self.file_entry.pack(side=RIGHT, fill=X)
	self.file_entry.insert(END, printfile)

	#  Image printing controls:
	self.imgchecked = self.add_html_checkbox(
	    top, "Print images", imageflag)
	self.greychecked = self.add_html_checkbox(
	    top, "Reduce images to greyscale", greyscaleflag)

	#  Anchor-handling selections:
	self.footnotechecked = self.add_html_checkbox(
	    top, "Footnotes for anchors", footnoteflag)
	self.underchecked = self.add_html_checkbox(
	    top, "Underline anchors", underflag)

	if self.ctype != "text/html":
	    Frame(top, height=8).pack()

	fr = Frame(top)
	fr.pack(fill=X)
	self.fontsize = DoubleVar(top)
	self.fontsize.set(fontsize)
	Label(fr, text="Base font size:").pack(side=LEFT)
	e = Entry(fr, textvariable=self.fontsize, width=5)
	e.pack(side=LEFT)
	e.bind('<Return>', self.return_event)
	self.leading = DoubleVar(top)
	self.leading.set(leading)
	Label(fr, text="Leading:").pack(side=LEFT)
	e = Entry(fr, textvariable=self.leading, width=5)
	e.pack(side=LEFT)
	e.bind('<Return>', self.return_event)

	#  Command buttons:
	ok_button = Button(botframe, text="OK",
			   command=self.ok_command)
	ok_button.pack(side=LEFT)
	cancel_button = Button(botframe, text="Cancel",
			       command=self.cancel_command)
	cancel_button.pack(side=RIGHT)
	tktools.unify_button_widths(ok_button, cancel_button)

	self.root.protocol('WM_DELETE_WINDOW', self.cancel_command)
	self.root.bind("<Alt-w>", self.cancel_event)
	self.root.bind("<Alt-W>", self.cancel_event)

	self.cmd_entry.bind('<Return>', self.return_event)
	self.file_entry.bind('<Return>', self.return_event)

	tktools.set_transient(self.root, self.master)

	self.check_command()
	self.root.grab_set()

    def add_html_checkbox(self, root, description, value):
	var = BooleanVar(root)
	var.set(value)
	if self.ctype == "text/html":
	    Checkbutton(root, text=description, variable=var).pack(anchor=W)
	return var

    def return_event(self, event):
	self.ok_command()
	
    def check_command(self):
	if self.checked.get():
	    self.file_entry['state'] = NORMAL
	    self.cmd_entry['state'] = DISABLED
	    self.file_entry.focus_set()
	else:
	    self.file_entry['state'] = DISABLED
	    self.cmd_entry['state'] = NORMAL
	    self.cmd_entry.focus_set()

    def ok_command(self):
	if self.checked.get():
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
	    except NameError:
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
	from html2ps import PSWriter, PrintingHTMLParser
	from html2ps import disallow_anchor_footnotes

	w = PSWriter(fp, self.title, self.url)
	if self.ctype == 'text/html':
	    imgloader = (self.imgchecked.get() and self.image_loader) or None
	    grey = self.greychecked.get()
	    fontsize = self.fontsize.get()
	    leading = self.leading.get()
	    p = PrintingHTMLParser(w, baseurl=self.context.baseurl(),
				   image_loader=imgloader, greyscale=grey,
				   underline_anchors=self.underchecked.get(),
				   leading=leading, fontsize=fontsize)
	    if not self.footnotechecked.get():
		p.add_anchor_transform(disallow_anchor_footnotes)
	    p.iconpath = self.context.app.iconpath
	elif self.ctype == 'text/plain':
	    p = PrintingTextParser(w)
	p.feed(self.infp.read())
	self.infp.close()
	p.close()
	w.close()

    def goaway(self):
	global printcmd, printfile, fileflag, imageflag, greyscaleflag
	global underflag, footnoteflag, leading, fontsize
	printcmd = self.cmd_entry.get()
	printfile = self.file_entry.get()
	fileflag = self.checked.get()
	footnoteflag = self.footnotechecked.get()
	greyscaleflag = self.greychecked.get()
	imageflag = self.imgchecked.get()
	underflag = self.underchecked.get()
	fontsize = self.fontsize.get()
	leading = self.leading.get()
	self.root.destroy()

    def image_loader(self, url):
	"""Image loader for the PrintingHTMLParser instance.
	"""
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
