# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""General Grail preferences panel."""

__version__ = "$Revision: 1.7 $"
# $Source: /home/john/Code/grail/src/prefpanels/PrintingPanel.py,v $

import html2ps
import PrefsPanels
import string
import Tkinter


GROUP = "printing"


class FontSizeVar(Tkinter.StringVar):
    _default = "10.0 / 10.7"
    def get(self):
	sizes = html2ps.parse_fontsize(Tkinter.StringVar.get(self))
	return "%s / %s" % sizes

    def set(self, value):
	sizes = html2ps.parse_fontsize(value)
	return Tkinter.StringVar.set(self, "%s / %s" % sizes)


class StringSetVar(Tkinter.StringVar):
    def get(self):
	return string.lower(Tkinter.StringVar.get(self))

    def set(self, value):
	value = string.capitalize(value)
	return Tkinter.StringVar.set(self, value)


class PrintingPanel(PrefsPanels.Framework):
    """Printing preferences."""

    # Class var for help button - relative to grail-home-page.
    HELP_URL = "help/prefs/printing.html"

    def CreateLayout(self, name, frame):

	# Printer configs are simple enough to use the convenience functions
	self.PrefsEntry(frame, 'Print command: ',
			GROUP, 'command',
			entry_width=20, label_width=16)
	self.PrefsCheckButton(frame, "Images: ", "Print images ",
			      GROUP, 'images',
			      label_width=16)
	self.PrefsCheckButton(frame, " ", "Reduce images to greyscale",
			      GROUP, 'greyscale',
			      label_width=16)
	self.PrefsCheckButton(frame, "Anchors: ", "Footnotes for anchors",
			      GROUP, 'footnote-anchors',
			      label_width=16)
	self.PrefsCheckButton(frame, " ", "Underline anchors",
			      GROUP, 'underline-anchors',
			      label_width=16)
	# paper size:
	var = StringSetVar()
	sizes = html2ps.paper_sizes.keys()
	sizes.sort()
	sizes = map(string.capitalize, sizes)
	self.PrefsOptionMenu(frame, "Paper size: ", GROUP, 'paper-size',
			     sizes, label_width=16, variable=StringSetVar())
	# page orientation:
	var = StringSetVar()
	opts = html2ps.paper_rotations.keys()
	opts.sort()
	opts = map(string.capitalize, opts)
	self.PrefsOptionMenu(frame, "Orientation: ", GROUP, 'orientation',
			     opts, label_width=16, variable=StringSetVar())
	# font size and leading:
	self.PrefsEntry(frame, "Font size: ",
			GROUP, 'font-size',
			typename='string', entry_width=12,
			label_width=16, variable=FontSizeVar())
