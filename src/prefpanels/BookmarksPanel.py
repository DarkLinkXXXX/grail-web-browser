"""Bookmarks and History preferences panel."""

__version__ = '$Revision: 1.1 $'
# $Source: /home/john/Code/grail/src/prefpanels/BookmarksPanel.py,v $

import PrefsPanels
from Tkinter import *
import tktools
from Bookmarks import NEW_AT_BEG, NEW_AT_END, NEW_AS_CHILD, \
                      BMPREFGROUP, COLLAPSE_PREF, INCLUDE_PREF, ADDLOC_PREF



class BookmarksPanel(PrefsPanels.Framework):
    """Preferences for Bookmarks and History"""

    # class var for help button -- relative to the grail home page
    HELP_URL = 'help/prefs/bookmarks.html'

    def CreateLayout(self, name, frame):
	bmframe = Frame(frame)
	bmframe.pack(fill=BOTH, expand=1)

	self.PrefsCheckButton(bmframe, 'Bookmark Headers:',
			      'Collapse Aggressively',
			      BMPREFGROUP, COLLAPSE_PREF)

	addcurloc = StringVar()
	addcur_frame = Frame(bmframe)
	addcur_frame.pack()
	label = Label(addcur_frame, text='Add Current Page:')
	label.pack(side=LEFT, anchor=E)
	choices_frame = Frame(addcur_frame, relief=SUNKEN, borderwidth=1)
	choices_frame.pack(side=LEFT)

	prepends = Radiobutton(choices_frame, text='Prepends to File',
			       variable=addcurloc,
			       value=NEW_AT_BEG)
	prepends.pack(fill=BOTH, expand=1)

	appends = Radiobutton(choices_frame, text='Appends to File',
			      variable=addcurloc,
			      value=NEW_AT_END)
	appends.pack(fill=BOTH, expand=1)

	childsib = Radiobutton(choices_frame,
			       text="As Selection's Child or Sibling",
			       variable=addcurloc,
			       value=NEW_AS_CHILD)
	childsib.pack(fill=BOTH, expand=1)

	self.PrefsCheckButton(bmframe, "Browser's Pulldown Menu:",
			      'Includes Bookmark Entries',
			      BMPREFGROUP, INCLUDE_PREF)

	self.RegisterUI(BMPREFGROUP, ADDLOC_PREF, 'string',
			addcurloc.get, addcurloc.set)
