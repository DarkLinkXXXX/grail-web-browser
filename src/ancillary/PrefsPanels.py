"""Framework for implementing GUI dialogs user preference group editing."""

__version__ = "$Revision: 2.2 $"
# $Source: /home/john/Code/grail/src/ancillary/PrefsPanels.py,v $

import sys, os

import GrailPrefs

from Tkinter import *
import tktools
import grailutil
import tktools
import string

# Setting this from PrefsDialogs module gives you reload-button for
# incremental development of your dialogs.
DEBUG=0

# ########################### Initialization ########################### #

BrowserState = {'dialogs': [], 'browser': None, 'app': None,
		'root': None}

def PrefsDialogsSetup(menu, browser):
    """Establish menu and browser state for use by dialogs.

    Should be invoked by mainline Grail code."""
    global BrowserState

    BrowserState['menu'] = menu
    BrowserState['browser'] = browser
    BrowserState['root'] = browser.root

    # BrowserState['dialogs'] is already populated by Framework.__init__().
    for dialog in BrowserState['dialogs']:
	menu.add_command(label=dialog.title, command=dialog.Post)

    BrowserState['prefs'] = prefs = browser.app.prefs
    # Create lookup table for use by Framework._set_widgets() method:
    BrowserState['get-methods'] = {'string': prefs.Get, 'int': prefs.GetInt,
				   'float': prefs.GetFloat,
				   'Boolean': prefs.GetBoolean}

# ########################### Framework ########################### #

class Framework:
    """Skeleton for building preferences dialogs via inheritance.

    The framework provides general controls, like save/revert/resume, and a
    mechanism for associating the User Inteface elements with preferences,
    so the preferences are systematically revised when the changes are
    committed.

    To build a preferences dialog:

     - Inherit from this class.
     - Invoke the base .__init__() from your derived  .__init__().
     - implement preference-category-specific layout by overriding the
       .CategoryLayout() method.
     - Use the .RegisterUI() to couple the widget (or other) acccessor
       routines with the corresponding preference.

    Your dialog will be included in the Preferences menu bar pulldown, and
    will be posted when its entry is selected."""

    def __init__(self, category):
	"""Invoke from category-specific __init__."""
	self._category = category
	self._collection = {}
	self.title = category + ' Preferences'
	self._widget = None
	# Register on comprehensive list.
	BrowserState['dialogs'].append(self)

    # Preferences-specific layout method - override!
    def CategoryLayout(self, frame):
	"""User should override this method with their own layout."""
	raise (SystemError,
	       '.CategoryLayout() should be overridden in derived class.')

    # Use this routine in category layout to associate preference with the
    # user interface mechanism for setting them.
    def RegisterUI(self, group, component, type, UIget, UIset):
	"""Associate preference GROUP/COMPONENT UI setting mechanism.

	The registered info is used to put established values in the widget
	and check for changed values when the dialog session is applied."""

	self._collection[(group, component)] = (type, UIget, UIset)

    def Post(self):
	"""Call from menu interface to engage dialog."""

	if not self._widget:
	    self._create_widget()
	else:
	    self._widget.deiconify()
	    self._widget.tkraise()
	self._poll_modified()

    def _create_widget(self):
	self._frame = BrowserState['root']
	widget = self._widget = Toplevel(self._frame, class_='Grail')
	widget.title(self.title)
	tktools.install_keybindings(widget)
	widget.bind('<Return>', self._done)
	widget.bind('<KeyRelease>', self._poll_modified)
	widget.bind('<Button>', self._poll_modified)

	width=80			# Of the settings frame.

	#self._title_widget = Label(widget, text=self.title, relief='raised',
	#			   bd=2)
	#self._title_widget.pack(side='top', padx='2m', pady='2m',
	#			ipadx='3m', ipady='2m')

	# Frame for the user to build within:
	container = Frame(widget, width=(width + 10), relief='groove', bd=2)
	container.pack(side='top', fill='x', padx='4m', pady='2m')
	self.framework_widget = Frame(container)
	self.framework_widget.pack(side='top', fill='x', padx='2m', pady='2m')

	self._create_disposition_bar(widget)

	# Do the user's setup:
	self.CategoryLayout(self.framework_widget)

	# And now initialize the widget values:
	self._set_widgets()
	

    def _create_disposition_bar(self, frame):
	bar = Frame(frame)
	bartop = Frame(bar)
	bartop.pack(side=TOP)
	barbottom = Frame(bar)
	barbottom.pack(side=BOTTOM)
	donebtn = Button(bartop, text="OK", command=self._done)
	cancelbtn = Button(bartop, text="Cancel", command=self._cancel)
	self._applybtn = Button(barbottom, text="Apply",
				command=self._apply)
	self._revertbtn = Button(barbottom, text="Revert",
				 command=self._revert)
	self._factory_defaults_btn = Button(barbottom,
					    command=self._factory_defaults,
					    text="Factory Defaults")
	donebtn.pack(side='left')
	self._applybtn.pack(side='left')
	self._revertbtn.pack(side='right')
	self._factory_defaults_btn.pack(side='right')
	cancelbtn.pack(side='right')
	if DEBUG:
	    reloadbtn = Button(bartop, text="(reload)",
			       command=self.reload_module)
	    reloadbtn.pack(side='right')

	bartop.pack(fill='both')
	barbottom.pack(fill='both')
	bar.pack(fill='both')

    # Operational commands:
    def _set_widgets(self, factory=0):
	"""Initialize dialog widgets with preference db values.

	Optional FACTORY true means use system defaults for values."""
	for (g, c), (type, UIget, UIset) in self._collection.items():
	    UIset(BrowserState['get-methods'][type](g, c, factory))

    def _done(self, event=None):
	"""Conclude dialog: commit and withdraw it."""
	self._apply()
	self._hide()

    def _apply(self):
	"""Apply settings from dialog to preferences."""
	prefsset = BrowserState['prefs'].Set
	# Snarf the settings from the widgets:
	for (g, c), (type, UIget, UIset) in self._collection.items():
	    prefsset(g, c, UIget())
	BrowserState['prefs'].Save()
	self._poll_modified()

    def _factory_defaults(self):
	"""Reinit dialog widgets with system-defaults preference db values."""
	self._set_widgets(factory=1)
	self._poll_modified()

    def _revert(self):
	"""Return settings to currently applied ones."""
	prefsget = BrowserState['get-methods']['string']
	# Snarf the settings from the widgets:
	for (g, c), (type, UIget, UIset) in self._collection.items():
	    UIset(prefsget(g, c))
	self._poll_modified()
	
    def _cancel(self):
	self._hide()
	self._revert()

    def _hide(self):
	self._widget.withdraw()

    def reload_module(self):
	"""Handy routine, used if DEBUG true, to reload the module within a
	single grail session."""
	# We retain some state around the reload, including the prior
	# versions of the dialogs.
	menu, browser = BrowserState['menu'], BrowserState['browser']
	import PrefsDialogs
	# Retain callbacks, since grail isn't restarting to reestablish them:
	callbacks = BrowserState['prefs']._callbacks
	reload(GrailPrefs)
	BrowserState['prefs']._callbacks = callbacks
	reload(sys.modules[__name__])
	reload(PrefsDialogs)
	PrefsDialogsSetup(menu, browser)
	self._hide()

    # State mechanisms.

    def _visible_p(self):
	return self._frame.state() <> 'withdrawn'

    def _poll_modified(self, event=None):
	"""Check for changes and enable disposition buttons accordingly."""
	# First, post an update for prompt user feedback:
	self._widget.update_idletasks()
	# Apply and Revert w.r.t. saved settings:
	if  self._modified_p():
	    self._applybtn.config(state='normal')
	    self._revertbtn.config(state='normal')
	else:
	    self._applybtn.config(state='disabled')
	    self._revertbtn.config(state='disabled')
	# Factory Defaults w.r.t. factory settings:
	if self._modified_p(factory=1):
	    self._factory_defaults_btn.config(state='normal')
	else:
	    self._factory_defaults_btn.config(state='disabled')

    def _modified_p(self, factory=0):
	"""True if any UI setting in the dialog is different than saved.

	If optional FACTORY is true, compare only with factory defaults."""
	prefsget = BrowserState['get-methods']['string']
	for (g, c), (type, UIget, UIset) in self._collection.items():
	    if UIget() != prefsget(g, c, factory):
		return 1
	return 0
