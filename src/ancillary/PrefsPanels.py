"""Framework for implementing GUI dialogs for editing of user preferences.

Loads preference modules in GRAILROOT/prefpanels/*prefs.py and
~user/.grail/prefpanels/*prefs.py."""

__version__ = "$Revision: 2.5 $"
# $Source: /home/john/Code/grail/src/ancillary/PrefsPanels.py,v $

import sys, os
import imp

if __name__ == "__main__":
    # For operation outside of Grail:
    grail_root = '..'
    sys.path = [grail_root, '../utils', '../pythonlib'] + sys.path

import GrailPrefs

from Tkinter import *
import tktools
import grailutil
import string, regex, regsub


DIALOG_CLASS_NAME_SUFFIX = 'Panel'

GET_METHODS = {'string': 'Get', 'int': 'GetInt', 'float': 'GetFloat',
	       'Boolean': 'GetBoolean'}

from __main__ import grail_root

# User's panels dir should come after sys, so user's takes precedence.
dialogs_dirs = [os.path.join(grail_root, 'prefspanels'),
		os.path.expanduser("~/.grail/prefspanels")]

modname_matcher = regex.compile("^\(.*\)prefs.py[c]?$")

# Framework

class Framework:
    """Skeleton for building preferences dialogs via inheritance.

    The framework provides general controls, like save/revert/resume, and a
    mechanism for associating the User Interface elements with preferences,
    so the preferences are systematically revised when the changes are
    committed.

    To build a preferences dialog:

     - Create a class which inherit from this one, and is named with the
       concatenation of the dialog name and "Panel", eg "GeneralPanel".
     - Implement dialog-specific layout by overriding the .CreateLayout()
       method.
       - Within .CreateLayout, use the self.RegisterUI() to couple the
         widget (or whatever user interface element) with the corresponding
         preference.  (.widget_set_func() is useful for producing the uiset
         func for many tkinter widgets.) 
       - There are also some convenient routines for making widgets, eg
         self.PrefsCheckButton().

    Your dialog will be included in the Preferences menu bar pulldown, and
    will be posted when its entry is selected."""

    def __init__(self, name, app):
	"""Invoke from category-specific __init__."""
	self.collection = {}
	self.app = app
	self.frame = app.root
	self.name = name
	self.title = self.name + ' Preferences'
	self.widget = None
	self.prev_settings = {}

    # Mandatory preferences-specific layout method.
    def CreateLayout(self, name, frame):
	"""Override this method with specific layout."""
	raise SystemError, "Derived class should override .CreateLayout()"

    # Optional preferences-specific delete method.
    def Dismiss(self):
	"""Override this method for cleanup on dismissal, if any."""
	pass

    # Use this routine in category layout to associate preference with the
    # user interface mechanism for setting them.
    def RegisterUI(self, group, component, type, uiget, uiset):
	"""Associate preference with User Interface setting mechanism.

	Preference is specified by group and component.  Type is used for
	choice of preference-get funcs.  uiget and uiset should be routines
	that obtain and impose values on the dialog widget representing the
	preference.  (.widget_set_func() is useful for producing the uiset
	func for many tkinter widgets.)"""

	self.collection[(group, component)] = (type, uiget, uiset)

    # Helpers

    def PrefsCheckButton(self, frame, general, specific, group, component,
			 left_width=25):
	"""Handy utility for creating checkbutton preferences widgets.

	A label and a button are packed in 'frame' arg, using text of
	'general' arg for title and of 'specific' arg for button label.
	The preferences variable is specified by 'group' and 'component'
	args, and an optional 'left_width' arg specifies how much space
	should be assigned to the general-label side of the thing."""
	f = Frame(frame)
	var = StringVar()
	l = Label(f, text=general, width=left_width, anchor=E)
	l.pack(side=LEFT)
	cb = Checkbutton(f, text=specific, relief='ridge', bd=1, variable=var)
	cb.pack(side=LEFT)
	f.pack(fill=X, side=TOP, pady='1m')
	self.RegisterUI(group, component, 'Boolean', var.get, var.set)

    def widget_set_func(self, widget):
	"""Return routine to be used to set widget.
	    
	    The returned routine takes a single argument, the new setting."""
	v = StringVar()
	widget.config(textvariable=v)
	return v.set

    def post(self, browser):
	"""Called from menu interface to engage dialog."""

	if not self.widget:
	    self.create_widget()
	else:
	    self.widget.deiconify()
	    self.widget.tkraise()
	# Stash the browser from which we were last posted, in case the
	# panel code needs to know...
	self.browser = browser

	self.poll_modified()

    def create_widget(self):
	widget = self.widget = Toplevel(self.frame, class_='Grail')
	widget.title(self.title)
	tktools.install_keybindings(widget)
	widget.bind('<Return>', self.done_cmd)
	widget.bind('<Key>', self.poll_modified)
	widget.bind('<Button>', self.poll_modified)
	widget.bind("<Alt-w>", self.cancel_cmd)
	widget.bind("<Alt-W>", self.cancel_cmd)
	widget.bind("<Alt-Control-r>", self.reload_panel_cmd) # Unadvertised
	widget.bind('<Button>', self.poll_modified)
	widget.protocol('WM_DELETE_WINDOW', self.cancel_cmd)

	width=80			# Of the settings frame.

	# Frame for the user to build within:
	container = Frame(widget, width=(width + 10), relief='groove', bd=2)
	container.pack(side='top', fill='x', padx='4m', pady='2m')
	self.framework_widget = Frame(container)
	self.framework_widget.pack(side='top', fill='x', padx='2m', pady='2m')

	self.create_disposition_bar(widget)

	# Do the user's setup:
	self.CreateLayout(self.name, self.framework_widget)

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

	bartop.pack(fill='both')
	barbottom.pack(fill='both')
	bar.pack(fill='both')

    # Operational commands:
    def set_widgets(self, factory=0):
	"""Initialize dialog widgets with preference db values.

	Optional FACTORY true means use system defaults for values."""
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    getter = getattr(self.app.prefs, GET_METHODS[type])
	    uiset(getter(g, c, factory))

    def done_cmd(self, event=None):
	"""Conclude dialog: commit and withdraw it."""
	self.apply_cmd()
	self.hide()

    def apply_cmd(self):
	"""Apply settings from dialog to preferences."""
	prefsset = self.app.prefs.Set
	# Snarf the settings from the widgets:
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    prefsset(g, c, uiget())
	self.app.prefs.Save()
	self.poll_modified()

    def factory_defaults_cmd(self):
	"""Reinit dialog widgets with system-defaults preference db values."""
	self.set_widgets(factory=1)
	self.poll_modified()

    def revert_cmd(self):
	"""Return settings to currently applied ones."""
	prefsget = getattr(self.app.prefs, GET_METHODS['string'])
	# Snarf the settings from the widgets:
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    uiset(prefsget(g, c))
	self.poll_modified()
	
    def cancel_cmd(self):
	self.hide()
	self.revert_cmd()

    def hide(self):
	self.Dismiss()
	self.widget.withdraw()

    def reload_panel_cmd(self, event=None):
	"""Unadvertised routine for reloading panel code during development."""
	# Zeroing the entry for the module will force an import, which
	# will force a reload if the code has been modified.
	self.hide()
	self.app.prefs_dialogs.load(self.name, reloading=1)

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

	prefsget = getattr(self.app.prefs, GET_METHODS['string'])
	for (g, c), (type, uiget, uiset) in self.collection.items():
	    if uiget() != prefsget(g, c, factory):
		return 1
	return 0

# Setup

class PrefsDialogsMenu:
    """Setup prefs dialogs and populate the browser menu."""

    def __init__(self, menu, browser):
	self.browser = browser
	self.app = browser.app
	self.menu = menu
	if hasattr(self.app, 'prefs_dialogs'):
	    self.dialogs = self.app.prefs_dialogs.dialogs
	else:
	    self.dialogs = {}
	    self.app.prefs_dialogs = self
	    for (nm, clnm, modnm, moddir) in self.discover_dialog_modules():
		if not self.dialogs.has_key(nm):
		    # [module name, class name, directory, instance]
		    self.dialogs[nm] = [modnm, clnm, moddir, None]
	for name in self.dialogs.keys():
	    # Enclose self and the name in a teeny leetle func:
	    def poster(self=self, name=name):
		self.do_post(name)
	    # ... which will be used to call the real posting routine:
	    menu.add_command(label=name, command=poster)

    def discover_dialog_modules(self):
	"""Identify candidate dialogs.

	Return list of tuples describing found dialog modules: (name,
	modname, moddir).

	Candidate modules must end in 'prefs.py' or 'prefs.pyc'.  The name
	is formed by extracting the prefix and substituting spaces for
	underscores (with leading and trailing spaces stripped).

	For multiple panels with the same name, the last one found is used."""
	got = {}
	for dir in dialogs_dirs:
	    entries = []
	    try:
		entries = os.listdir(dir)
	    except os.error:
		# Optional dir not there.
		pass
	    for entry in entries:
		if modname_matcher.match(entry) != -1:
		    name = regsub.gsub("_", " ", modname_matcher.group(1))
		    class_name = regsub.gsub("_", "",
					     modname_matcher.group(1))
		    got[name] = ((string.strip(name), class_name, entry, dir))
	return got.values()
		    
    def do_post(self, name):
	"""Expose the dialog, creating it if necessary."""
	entry = self.dialogs[name]
	if entry[3]:
	    # Already loaded:
	    entry[3].post(self.browser)
	else:
	    # Needs to be loaded:
	    if self.load(name):
		self.do_post(name)

    def load(self, name, reloading=0):
	"""Import the dialog module and init the instance.

	Returns 1 if successful, None otherwise."""
	entry = self.dialogs[name]
	try:
	    sys.path.insert(0, entry[2])
	    try:
		modnm = entry[0][:string.index(entry[0], '.')]
		mod = __import__(modnm)
		if reload:
		    reload(mod)
		class_name = (regsub.gsub(" ", "", name)
			      + DIALOG_CLASS_NAME_SUFFIX)
		# Instantiate it:
		entry[3] = getattr(mod, class_name)(name, self.app)
		return 1
	    except:
		# Whatever may go wrong in import or dialog post
		e, v, tb = sys.exc_type, sys.exc_value, sys.exc_traceback
		self.app.root.report_callback_exception(e, v, tb)
		return None
	finally:
	    try:
		sys.path.remove(entry[1])
	    except ValueError:
		pass

# Testing.

def standalone():
    """Provide standins for Grail objs so we can run outside of Grail."""
    class fake_app:
	def __init__(self, root):
	    self.prefs = GrailPrefs.AllPreferences()
	    self.root = root
	    root.report_callback_exception = self.report_callback_exception
	def report_callback_exception(self, e, v, tb):
	    print "Callback error: %s, %s" % (e, v)
	def register_on_exit(self, func): pass
	def unregister_on_exit(self, func): pass

    root = Frame()

    quitbutton = Button(root, text='quit')
    quitbutton.pack(side=LEFT)
    def quit(root=root): root.destroy(); sys.exit(0)
    quitbutton.config(command=quit)

    prefsbut = Menubutton(root, text="Preferences")
    prefsbut.pack(side=LEFT)
    prefsmenu = Menu(prefsbut)
    prefsbut['menu'] = prefsmenu
    root.pack(side=LEFT)

    app = fake_app(root)
    pdm = PrefsDialogsMenu(prefsmenu, app)
    prefsmenu.mainloop()
    del pdm

if __name__ == "__main__":
    standalone()
