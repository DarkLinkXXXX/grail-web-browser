"""General Grail preferences panel."""

__version__ = "$Revision: 1.2 $"
# $Source: /home/john/Code/grail/src/prefpanels/GeneralPanel.py,v $

# Base class for the dialog:
import PrefsDialogs

import sys, os

from Tkinter import *
import tktools
import grailutil
import tktools
import string

# ########################### Specific dialogs ########################### #

class GeneralPanel(PrefsDialogs.Framework):
    """Miscellaneous preferences relating to the browser, startup, and
    other behaviors that don't fit in specific preferences categories."""

    def CreateLayout(self, name, frame):

	# Home page: basic entry-based prefs can be as simple as this one:
	e, l, f = tktools.make_labeled_form_entry(frame, 'Home page:',
						  40, 1, 25)
	# Couple the widgets with the preferences:
	self.RegisterUI('landmarks', 'home-page', 'string',
			e.get, self.widget_set_func(e))

	# Geometry: more customized widgets (like this composite entry)
	# 	    may involve more UI:
	f = Frame(frame)
	l = Label(f, text="Browser geometry:", width=25, anchor=E)
	l.pack(side=LEFT)
	entries_frame = Frame(f, relief='ridge', bd=1)
	wl = Label(entries_frame, text="Width:"); wl.pack(side=LEFT)
	we = Entry(entries_frame, width=3); we.pack(side=LEFT)
	hl = Label(entries_frame, text="Height:"); hl.pack(side=LEFT)
	he = Entry(entries_frame, width=3); he.pack(side=LEFT)
	entries_frame.pack(side=LEFT)
	f.pack(fill=X, side=TOP, pady='1m')
	self.RegisterUI('browser', 'default-width', 'int',
			we.get, self.widget_set_func(we))
	self.RegisterUI('browser', 'default-height', 'int',
			he.get, self.widget_set_func(he))

	# Preferences needing just a CheckButton can use a tailored
	# routine, like these three:
	self.PrefsCheckButton(frame, "Initial page:", "Load on Grail startup",
			      'browser', 'load-initial-page')

	self.PrefsCheckButton(frame, "Image loading:", "Load inline images",
			      'browser', 'load-images')

	self.PrefsCheckButton(frame,
			      "HTML parsing:", "Advanced SGML recognition",
			      'parsing-html', 'strict')

	self.PrefsCheckButton(frame,
			      "Smooth scrolling:",
			      "Install smooth scrolling hack on new windows",
			      'browser', 'smooth-scroll-hack')

	frame.pack()
