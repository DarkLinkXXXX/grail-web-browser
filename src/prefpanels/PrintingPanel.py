"""General Grail preferences panel."""

__version__ = "$Revision: 1.4 $"
# $Source: /home/john/Code/grail/src/prefpanels/PrintingPanel.py,v $

# Base class for the panel:
import PrefsPanels

class PrintingPanel(PrefsPanels.Framework):
    """Printing preferences."""

    # Class var for help button - relative to grail-home-page.
    HELP_URL = "help/prefs/printing.html"

    def CreateLayout(self, name, frame):

	# Printer configs are simple enough to use the convenience functions
	self.PrefsEntry(frame, 'Print command: ',
			'printing', 'command',
			entry_width=20, label_width=16)
	self.PrefsCheckButton(frame, "Images: ", "Print images ",
			      'printing', 'images',
			      label_width=16)
	self.PrefsCheckButton(frame, " ", "Reduce images to greyscale",
			      'printing', 'greyscale',
			      label_width=16)
	self.PrefsCheckButton(frame, "Anchors: ", "Footnotes for anchors",
			      'printing', 'footnote-anchors',
			      label_width=16)
	self.PrefsCheckButton(frame, " ", "Underline anchors",
			      'printing', 'underline-anchors',
			      label_width=16)
	self.PrefsEntry(frame, "Base font size: ",
			'printing', 'base-font-size',
			typename='float', entry_width=4,
			label_width=16)
	self.PrefsEntry(frame, "Leading: ", 'printing', 'leading',
			typename='float', entry_width=4,
			label_width=16)
