"""Grail style preferences panel."""

__version__ = "$Revision: 1.5 $"
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
	style_families = string.split(self.app.prefs.Get('styles',
							 'all-families'))

	self.PrefsRadioButtons(frame, "Font size group:", style_sizes,
			       'styles', 'size', label_width=20)
	self.PrefsRadioButtons(frame, "Font Family:", style_families,
			       'styles', 'family', label_width=20)
	# Anchors:
	
	v = StringVar()
	f = Frame(frame)
	l = self.PrefsWidgetLabel(f, "Anchors:", label_width=20)
	cb = Checkbutton(f, text="Underline", relief='ridge', bd=1,
			 variable=v)
	cb.pack(side=LEFT)
	f.pack(fill=NONE, side=LEFT, pady='1m')
	self.RegisterUI('styles-common', 'history-ahist-underline',
			'Boolean', v.get, v.set)
	self.RegisterUI('styles-common', 'history-atemp-underline',
			'Boolean', v.get, v.set)
	self.RegisterUI('styles-common', 'history-a-underline',
			'Boolean', v.get, v.set)

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
