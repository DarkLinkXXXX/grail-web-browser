"""Grail style preferences panel."""

__version__ = "$Revision: 1.2 $"
# $Source: /home/john/Code/grail/src/prefpanels/StylePanel.py,v $

# Base class for the dialog:
import PrefsDialogs

import sys, os

from Tkinter import *
import tktools
import grailutil
import tktools
import string

# ########################### Specific dialogs ########################### #

class StylePanel(PrefsDialogs.Framework):
    """Dialog for selecting viewer presentation styles."""

    def CreateLayout(self, name, frame):

	choices = self.app.prefs.Get('styles', 'allgroups')

	# XxX PRELIMINARY, just to show it works!
	# Style group will use a radiobutton, and we will have selections
	# for the common styles, like color, underline, etc.

	self.PrefsEntry(frame,
			("Default style\n** %s **:\n(%s)" %
			 (choices, "i know, it should\nbe a radiobutton")),
			'styles', 'group', entry_width=15)

	frame.pack()
