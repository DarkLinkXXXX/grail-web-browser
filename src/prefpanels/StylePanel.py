"""Grail style preferences panel."""

__version__ = "$Revision: 1.4 $"
# $Source: /home/john/Code/grail/src/prefpanels/StylePanel.py,v $

# Base class for the panel:
import PrefsPanels

import sys, os

from Tkinter import *
import tktools
import grailutil
import tktools
import string

class StylePanel(PrefsPanels.Framework):
    """Panel for selecting viewer presentation styles."""

    def CreateLayout(self, name, frame):

	style_sizes = string.split(self.app.prefs.Get('styles',
						      'all-sizes'))
	style_types = string.split(self.app.prefs.Get('styles',
						      'all-types'))

	self.PrefsRadioButtons(frame, "Font size group:", style_sizes,
			       'styles', 'size')
	self.PrefsRadioButtons(frame, "Font Type:", style_types,
			       'styles', 'type')
	# Anchors:
	self.anchor_style_item(Frame(frame), "Fresh",
			       'styles-a-foreground', 'styles-a-underline')

	frame.pack()

    def anchor_style_item(self, frame, which, fore_cmpnt, under_cmpnt):
	f = Frame(frame)
	self.PrefsWidgetLabel(f, "%s anchor style:" % which)
	wf = Frame(f, relief=SUNKEN, bd=2)
	fore_msg = "Foreground color" 
	self.PrefsEntry(wf, fore_msg,
			'styles-common', fore_cmpnt,
			label_width=len(fore_msg) + 2, entry_width=9)
	under_msg = "Underline"
	self.PrefsCheckButton(wf, None, under_msg,
			      'styles-common', under_cmpnt)
	f.pack(fill=X, side=TOP, pady='1m')
	frame.pack()
