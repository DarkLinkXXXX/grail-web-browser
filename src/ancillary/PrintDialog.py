"""Print Dialog for Grail Browser.

This displays a really basic modal dialog, containing:

	- the print command (which should take PostScript from stdin
	  or a %s can be placed on the command line where the filename
	  of a file containing the postscript output will be placed)
	- a check box for printing to a file
	- the filename (to receive the PostScript instead)
	- an OK button
	- a Cancel button

The last state (print command, check box, filename) is saved in
globals  variables.

The dialog is modal by virtue of grabbing the focus and running
the Tk mainloop recursively.

When OK is activated, the HTML file is read using urllib.urlopen() and
the html2ps.PSWriter class is used to generate the PostScript.

When Cancel is actiavted, the dialog state is still saved.

"""


from Tkinter import *
import tktools
import os
import string
import Reader

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

global_prefs = None


def update_options(prefs=None):
    """Load/reload preferences.
    """
    global printcmd, printfile, fileflag, imageflag, greyscaleflag
    global underflag, footnoteflag, global_prefs, leading
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
    if not printcmd:
	printcmd = PRINTCMD


class PrintDialog:

    def __init__(self, context, url, title):
	try:
	    self.infp = context.app.open_url_simple(url)
	except IOError, msg:
	    context.error_dialog(IOError, msg)
	    return
	try:
	    self.ctype = self.infp.info()['content-type']
	except KeyError:
	    context.error_dialog("No type",
			"Documents of unknown type cannot be printed.")
	    return

	types = string.splitfields(self.ctype, '/')
	if types and types[0] == 'text':
	    if types[1] != 'html':
		self.ctype = 'text/plain'
	if self.ctype not in ('text/html', 'text/plain'):
	    context.error_dialog("Unprintable document",
				 "This document cannot be printed.")
	    return

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
	self.root = tktools.make_toplevel(self.master,
					  title="Print Dialog")
	self.root.iconname("Print Dialog")
	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    self.root, "Print command:")
	self.cmd_entry.insert(END, printcmd)

	#  Print to file controls:
	self.midframe = Frame(self.root)
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
	self.imgchecked = self.add_checkbox(
	    "Print images", imageflag)
	self.greychecked = self.add_checkbox(
	    "Reduce images to greyscale", greyscaleflag)

	#  Anchor-handling selections:
	self.footnotechecked = self.add_checkbox(
	    "Footnotes for anchors", footnoteflag)
	self.underchecked = self.add_checkbox(
	    "Underline anchors", underflag)

	#  Separator:
	fr = Frame(self.root, relief=SUNKEN, height=3, borderwidth=1)
	fr.pack(expand=1, fill=X)

	#  Command buttons:
	botframe = Frame(self.root)
	botframe.pack(side=BOTTOM, fill=X)

	ok_button = Button(botframe, text="OK",
			   command=self.ok_command)
	ok_button.pack(side=LEFT, padx='1m', pady='1m')
	cancel_button = Button(botframe, text="Cancel",
			       command=self.cancel_command)
	cancel_button.pack(side=RIGHT, padx='1m', pady='1m')
	#  this seems about the only way to get both of these the same width;
	#  should not have to rely on "average characters":
	width = len("Cancel")
	ok_button['width'] = width
	cancel_button['width'] = width

	self.root.protocol('WM_DELETE_WINDOW', self.cancel_command)
	self.root.bind("<Alt-w>", self.cancel_event)
	self.root.bind("<Alt-W>", self.cancel_event)

	self.cmd_entry.bind('<Return>', self.return_event)
	self.file_entry.bind('<Return>', self.return_event)

	tktools.set_transient(self.root, self.master)

	self.check_command()
	self.root.grab_set()

    def add_checkbox(self, description, value):
	var = IntVar(self.root)
	var.set(value)
	Checkbutton(self.root, text=description, variable=var).pack(anchor=W)
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
	self.root['cursor'] = 'watch'
	self.cmd_entry['cursor'] = 'watch'
	self.file_entry['cursor'] = 'watch'
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
	    p = PrintingHTMLParser(w, baseurl = self.context.baseurl(),
				   image_loader = imgloader, greyscale = grey,
				   underline_anchors = self.underchecked.get(),
				   leading = leading)
	    if not self.footnotechecked.get():
		p.add_anchor_transform(disallow_anchor_footnotes)
	    from GrailHTMLParser import GrailHTMLParser	## ???
	    p.iconpath = self.context.app.iconpath
	elif self.ctype == 'text/plain':
	    p = PrintingTextParser(w)
	p.feed(self.infp.read())
	self.infp.close()
	p.close()
	w.close()

    def goaway(self):
	global printcmd, printfile, fileflag, imageflag, greyscaleflag
	global underflag, footnoteflag, leading
	printcmd = self.cmd_entry.get()
	printfile = self.file_entry.get()
	fileflag = self.checked.get()
	footnoteflag = self.footnotechecked.get()
	greyscaleflag = self.greychecked.get()
	imageflag = self.imgchecked.get()
	underflag = self.underchecked.get()
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
