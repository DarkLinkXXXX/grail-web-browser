from Tkinter import *
import tktools
import os

PRINTCMD = "lpr"

printcmd = PRINTCMD

class Printing:

    def __init__(self, browser, url):
	self.browser = browser
	self.master = self.browser.root
	self.url = url
	self.root = Toplevel(self.master)
	self.cmd_entry, dummyframe = tktools.make_form_entry(
	    self.root, "Print command:")
	self.cmd_entry.delete('0', END)
	self.cmd_entry.insert(END, printcmd)

	self.midframe = Frame(self.root)
	self.midframe.pack(side=TOP, fill=X)

	self.checked = IntVar(self.root)
	self.file_check = Checkbutton(self.midframe,
				      command=self.check_command,
				      variable=self.checked)
	self.file_check.pack(side=LEFT)
	self.file_entry, dummyframe = tktools.make_form_entry(
	    self.midframe, "Print to file:")
	self.file_entry['state'] = DISABLED
	self.file_entry.pack(side=RIGHT)

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
	self.cmd_entry.focus_set()

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
	self.print_to_fp(fp)
	sts = fp.close()
	if sts:
	    self.browser.error_dialog("Exit",
				      "Print command exit status %s" % `sts`)
	self.goaway()

    def cancel_command(self):
	self.goaway()

    def print_to_fp(self, fp):
	self.browser.error_dialog("Sorry", "Printing will be supported soon")

    def goaway(self):
	global printcmd
	printcmd = self.cmd_entry.get()
	self.root.destroy()
