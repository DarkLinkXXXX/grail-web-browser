"""Framework for implementing GUI dialogs user preference group editing."""

__version__ = "$Revision: 2.3 $"
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

GET_METHODS = {'string': 'Get', 'int': 'GetInt', 'float': 'GetFloat',
	       'Boolean': 'GetBoolean'}

# BrowserState is going.
BrowserState = {'dialogs': [], 'browser': None, 'app': None, 'root': None}

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
    # Create lookup table for use by Framework.set_widgets() method:

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

    def __init__(self):
	"""Invoke from category-specific __init__."""
	self.collection = {}
	self.title = self.name + ' Preferences'
	self.widget = None
	self.prev_settings = {}
	# Register on comprehensive list.
	BrowserState['dialogs'].append(self)

    # Mandatory preferences-specific layout method.
    def CreateLayout(self, frame):
	"""Override this method with specific layout."""
	raise SystemError, "Derived class should override .CreateLayout()"

    # Optional preferences-specific delete method.
    def DeleteLayout(self):
	"""Override this method for deletion cleanup, if any."""
	pass

    # Use this routine in category layout to associate preference with the
    # user interface mechanism for setting them.
    def RegisterUI(self, group, component, type, uiget, uiset):
	"""Associate preference with User Interface setting mechanism.

	Preference is specified by group and component, and type is
	specified for 
	The registered info is used to put established values in the widget
	and check for changed values when the dialog session is applied."""

	self.collection[(group, component)] = (type, uiget, uiset)

    def PrefsCheckButton(self, frame, general, specific, group, component,
			 left_width=25):
	"""Handy utility for creating single-button preferences widgets.

	A label and a button are packed in 'frame' arg, using text of
	'general' arg for title and of 'specific' arg for button label.
	The preferences variable is specified by 'group' and 'component'
	args, and an optional 'left_width' arg specifies how much space
	should be assigned to the general-label side of the
	conglomerate."""
	f = Frame(frame)
	var = StringVar()
	l = Label(f, text=general, width=left_width, anchor=E)
	l.pack(side=LEFT)
	cb = Checkbutton(f, text=specific, relief='ridge', bd=1, variable=var)
	cb.pack(side=LEFT)
	f.pack(fill=X, side=TOP, pady='1m')
	self.RegisterUI(group, component, 'Boolean', var.get, var.set)

    def Post(self):
	"""Called from menu interface to engage dialog."""

	if not self.widget:
	    self.create_widget()
	else:
	    try:
		self.widget.deiconify()
		self.widget.tkraise()
	    except TclError:
		# Whoops, widget musta been destroyed - recreate:
		self.create_widget()
	self.poll_modified()

    def create_widget(self):
	self.frame = BrowserState['root']
	widget = self.widget = Toplevel(self.frame, class_='Grail')
	widget.title(self.title)
	tktools.install_keybindings(widget)
	widget.bind('<Return>', self.done_cmd)
	widget.bind('<Key>', self.poll_modified)
	widget.bind('<Button>', self.poll_modified)

	width=80			# Of the settings frame.

	# Frame for the user to build within:
	container = Frame(widget, width=(width + 10), relief='groove', bd=2)
	container.pack(side='top', fill='x', padx='4m', pady='2m')
	self.framework_widget = Frame(container)
	self.framework_widget.pack(side='top', fill='x', padx='2m', pady='2m')

	self.create_disposition_bar(widget)

	# Do the user's setup:
	self.CreateLayout(self.framework_widget)

	# And now initialize the widget values:
	self.set_widgets()
	

    def create_disposition_bar(self, frame):
	bar = Frame(frame)
	bartop = Frame(bar)
	bartop.pack(side=TOP)
	barbottom = Frame(bar)
	barbottom.pack(side=BOTTOM)
	done_btn = Button(bartop, text="OK", command=self.done_cmd)
	cancel_btn = Button(bartop, text="Cancel", command=self.cancel_cmd)
	self.apply_btn = Button(barbottom, text="Apply",
				command=self.apply_cmd)
	self.revert_btn = Button(barbottom, text="Revert",
				 command=self.revert_cmd)
	self.factory_defaults_btn = Button(barbottom,
					   command=self.factory_defaults_cmd,
					   text="Factory Defaults")
	done_btn.pack(side='left')
	self.apply_btn.pack(side='left')
	self.revert_btn.pack(side='right')
	self.factory_defaults_btn.pack(side='right')
	cancel_btn.pack(side='right')
	if DEBUG:
	    reload_btn = Button(bartop, text="(reload)",
				command=self.reload_module)
	    reload_btn.pack(side='right')

	bartop.pack(fill='both')
	barbottom.pack(fill='both')
	bar.pack(fill='both')

    # Operational commands:
    def set_widgets(self, factory=0):
	"""Initialize dialog widgets with preference db values.

	Optional FACTORY true means use system defaults for values."""
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    getter = getattr(BrowserState['prefs'], GET_METHODS[type])
	    uiset(getter(g, c, factory))

    def done_cmd(self, event=None):
	"""Conclude dialog: commit and withdraw it."""
	self.apply_cmd()
	self.hide()

    def apply_cmd(self):
	"""Apply settings from dialog to preferences."""
	prefsset = BrowserState['prefs'].Set
	# Snarf the settings from the widgets:
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    prefsset(g, c, uiget())
	BrowserState['prefs'].Save()
	self.poll_modified()

    def factory_defaults_cmd(self):
	"""Reinit dialog widgets with system-defaults preference db values."""
	self.set_widgets(factory=1)
	self.poll_modified()

    def revert_cmd(self):
	"""Return settings to currently applied ones."""
	prefsget = getattr(BrowserState['prefs'], GET_METHODS['string'])
	# Snarf the settings from the widgets:
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    uiset(prefsget(g, c))
	self.poll_modified()
	
    def cancel_cmd(self):
	self.hide()
	self.revert_cmd()

    def hide(self):
	self.widget.withdraw()

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
	self.hide()

    # State mechanisms.

    def poll_modified(self, event=None):
	"""Check for changes and enable disposition buttons accordingly."""
	# First, post an update for prompt user feedback:
	self.widget.update_idletasks()

	# Rectify disposition buttons if changes since last check:
	if self.modified_p():
	    self.apply_btn.config(state='normal')
	    self.revert_btn.config(state='normal')
	else:
	    self.apply_btn.config(state='disabled')
	    self.revert_btn.config(state='disabled')
	# Factory Defaults w.r.t. factory settings:
	if self.modified_p(factory=1):
	    self.factory_defaults_btn.config(state='normal')
	else:
	    self.factory_defaults_btn.config(state='disabled')

    def modified_p(self, factory=0):
	"""True if any UI setting is changed from saved.

	Optional 'factory' keyword means check wrt system default settings."""

	prefsget = getattr(BrowserState['prefs'], GET_METHODS['string'])
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    if uiget() != prefsget(g, c, factory):
		return 1
	return 0
