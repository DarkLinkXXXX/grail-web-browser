"""Print Dialog for Grail Browser.

This displays a really basic modal dialog, containing:

	- the print command (which should take PostScript from stdin)
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

PRINTCMD = "lpr"			# Default print command

# Global variables tracking the last contents of the dialog box
printcmd = PRINTCMD
printfile = ""
fileflag = 0


class PrintDialog:

    def __init__(self, browser, url, title):
	self.browser = browser
	self.url = url
	self.title = title
	self.master = self.browser.root
	self.root = tktools.make_toplevel(self.master,
					  title="Print Dialog")
	self.root.iconname("Print Dialog")
	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    self.root, "Print command:")
	self.cmd_entry.delete('0', END)
	self.cmd_entry.insert(END, printcmd)

	self.midframe = Frame(self.root)
	self.midframe.pack(side=TOP, fill=X)

	self.checked = IntVar(self.root)
	self.checked.set(fileflag)
	self.file_check = Checkbutton(self.midframe,
				      command=self.check_command,
				      variable=self.checked)
	self.file_check.pack(side=LEFT)
	self.file_entry, dummyframe = tktools.make_form_entry(
	    self.midframe, "Print to file:")
	self.file_entry.pack(side=RIGHT)
	self.file_entry.delete('0', END)
	self.file_entry.insert(END, printfile)

	self.botframe = Frame(self.root)
	self.botframe.pack(side=BOTTOM, fill=X)

	self.ok_button = Button(self.botframe, text="OK",
				command=self.ok_command)
	self.ok_button.pack(side=LEFT)
	self.cancel_button = Button(self.botframe, text="Cancel",
				    command=self.cancel_command)
	self.cancel_button.pack(side=RIGHT)

	self.cmd_entry.bind('<Return>', self.return_event)
	self.file_entry.bind('<Return>', self.return_event)

	tktools.set_transient(self.root, self.master)

	self.check_command()

	self.root.grab_set()

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
		self.browser.error_dialog("No file",
					  "Please enter a filename")
		return
	    try:
		fp = open(filename, "w")
	    except IOError, msg:
		self.browser.error_dialog(IOError, str(msg))
		return
	else:
	    cmd = self.cmd_entry.get()
	    if not cmd:
		self.browser.error_dialog("No command",
					  "Please enter a print command")
		return
	    try:
		fp = os.popen(cmd, "w")
	    except IOError, msg:
		self.browser.error_dialog(IOError, str(msg))
		return
	self.root['cursor'] = 'watch'
	self.cmd_entry['cursor'] = 'watch'
	self.file_entry['cursor'] = 'watch'
	self.root.update_idletasks()
	self.print_to_fp(fp)
	sts = fp.close()
	if sts:
	    self.browser.error_dialog("Exit",
				      "Print command exit status %s" % `sts`)
	self.goaway()

    def cancel_command(self):
	self.goaway()

    def print_to_fp(self, fp):
	from urllib import urlopen
	from html2ps import PSWriter
	from formatter import AbstractFormatter
	try:
	    infp = urlopen(self.url)
	except IOError, msg:
	    self.browser.error_dialog(IOError, msg)
	    return
	w = PSWriter(fp, self.title)
	f = AbstractFormatter(w)
	p = PrintingHTMLParser(f)
	p.feed(infp.read())
	infp.close()
	p.close()
	w.close()

    def goaway(self):
	global printcmd, printfile, fileflag
	printcmd = self.cmd_entry.get()
	printfile = self.file_entry.get()
	fileflag = self.checked.get()
	self.root.destroy()


from htmllib import HTMLParser


class PrintingHTMLParser(HTMLParser):

    """Class to override HTMLParser's default methods for anchors."""

    def anchor_bgn(self, href, name, type):
	self.anchor = href
	self.formatter.push_style(href and 'u' or None)

    def anchor_end(self):
	self.formatter.pop_style()
	self.anchor = None
