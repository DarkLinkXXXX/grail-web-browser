"""Preference panel to control applet privileges."""

import string
import urlparse
from Tkinter import *

import tktools

import PrefsDialogs

LABEL = "\
Enter applet group names (host names, or domain names with leading dot):"

HELP_URL = "help/prefs/applets.html"	# Relative to grail-home-page

class AppletsPanel(PrefsDialogs.Framework):

    name = 'Applet'

    def CreateLayout(self, name, frame):
	# Create GUI
	self.label = Label(frame, text=LABEL, anchor=W)
	self.label.pack(fill=X)
	self.textbox, self.textframe = tktools.make_text_box(frame,
							     width=40,
							     height=10)
	self.textbox.bind('<Return>', self.return_in_textbox)
	self.loadvar = StringVar()
	self.loadall = Radiobutton(frame,
				   text="Load all applets",
				   variable=self.loadvar,
				   value="all")
	self.loadall.pack(anchor=W)
	self.loadsome = Radiobutton(
	    frame,
	    text="Load applets in indicated groups only",
	    variable=self.loadvar,
	    value="some")
	self.loadsome.pack(anchor=W)
	self.loadnone = Radiobutton(frame
				    , text="Load no applets",
				    variable=self.loadvar,
				    value="none")
	self.loadnone.pack(anchor=W)
	self.helpbtn = Button(frame, text="Help", command=self.help)
	self.helpbtn.pack(side=BOTTOM, anchor=E)
	self.RegisterUI("applets", "groups", "string",
			self.getgroups, self.setgroups)
	self.RegisterUI("applets", "load", "string",
			self.loadvar.get, self.loadvar.set)

    def getgroups(self):
	data = self.textbox.get("1.0", END)
	words = string.split(data)
	return string.joinfields(words, "\n ")

    def setgroups(self, data):
	words = string.split(data)
	data = string.joinfields(words, "\n")
	self.textbox.delete("1.0", END)
	self.textbox.insert("1.0", data)

    def return_in_textbox(self, event):
	"""Redefine <Return> binding to prevent invoking the OK button."""
	self.textbox.insert(INSERT, '\n')
	return 'break'

    def help(self):
	"""Display help in the associated (or any old) browser."""
	from __main__ import app
	if not app.browsers:
	    print "No browser left to display help."
	    return
	browser = self.browser
	if not browser or not browser.valid():
	    browser = app.browsers[-1]	# Pick the last valid one
	    self.browser = browser
	grailhome = self.app.prefs.Get('landmarks', 'grail-home-page')
	browser.context.load(urlparse.urljoin(grailhome, HELP_URL))
	browser.root.tkraise()
