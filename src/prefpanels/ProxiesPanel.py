"""Grail proxy preferences panel."""

__version__ = "$Revision: 1.1 $"
# $Source: /home/john/Code/grail/src/prefpanels/ProxiesPanel.py,v $

# Base class for the dialog:
import PrefsPanels

from Tkinter import *
import grailutil

class ProxiesPanel(PrefsPanels.Framework):
    """Network preferences related to redirection of URL streams."""
    
    # Class var for help button - relative to grail-home-page.
    HELP_URL = "help/prefs/proxies.html"

    def CreateLayout(self, name, frame):
	"""create a bunch of widgets that look like a prefs panel."""

	#
	# Set up some frames
	proxy_frame = Frame(frame)
	manual_frame = Frame(proxy_frame)
	manual_right_frame = Frame(manual_frame)
	manual_left_frame = Frame(manual_frame)
	no_proxy_frame = Frame(proxy_frame)

	#
	# Establish some booleans to represent the button states
	self.no_proxy_enabled = BooleanVar()
	self.manual_proxy_enabled = BooleanVar()
	self.fb_state = BooleanVar()
	self.hb_state = BooleanVar()
	self.nb_state = BooleanVar()

	#
	# Set the Boolean vars to FALSE initially
	self.no_proxy_enabled.set(0)
	self.manual_proxy_enabled.set(0)
	self.fb_state.set(0)
	self.hb_state.set(0)
	self.nb_state.set(0)

	#
	# Create top level widgets
	l = Label(proxy_frame, pady=15,
	       text="A proxy allows your browser to access the Internet through a Firewall.")

	self.no = Checkbutton(proxy_frame,
	       text="Proxy Exceptions List            ",
	       variable=self.no_proxy_enabled,
	       padx=200, pady=15,
	       font='-*-helvetica-bold-o-normal-*-*-120-*-*-*-*-*-*' ,
	       command=self.no_switch)
	manual = Checkbutton(proxy_frame,
	       text="Manual Proxy Configuration ",
	       variable=self.manual_proxy_enabled,
	       padx=200, pady=15,
	       font='-*-helvetica-bold-o-normal-*-*-120-*-*-*-*-*-*',
	       command=self.manual_switch)
	
	self.he = Entry(manual_right_frame, relief=SUNKEN, width=38)
	self.hb = Checkbutton(manual_left_frame, relief=FLAT,
	       variable=self.hb_state,
	       text="HTTP Proxy (http://server:port):",
	       command=self.http_entry_toggle)
	self.fe = Entry(manual_right_frame, relief=SUNKEN, width=38)
	self.fb = Checkbutton(manual_left_frame, relief=FLAT,
	       variable=self.fb_state,
	       text=" FTP Proxy (http://server:port):",
	       command=self.ftp_entry_toggle)

	self.nb = Checkbutton(no_proxy_frame, relief=FLAT,
	       variable=self.nb_state,
	       text="Servers that need no proxy to be reached (www.python.org, www.dlib.org):",
	       command=self.no_proxy_entry_toggle)
	self.ne = Entry(no_proxy_frame, relief=SUNKEN, width=75)

	#
	# Pack the widgets
	frame.pack(expand=1, fill=X)
	proxy_frame.pack(expand=1, fill=X)
	l.pack(side=TOP)
	manual.pack(side=TOP, expand=1, anchor=CENTER, fill=X)
	manual_frame.pack(side=TOP, expand=1, fill=X)
	self.no.pack(side=TOP, expand=1, anchor=CENTER, fill=X)
	no_proxy_frame.pack(side=TOP, expand=1, fill=X)
	manual_right_frame.pack(side=RIGHT, expand=1, fill=X)
	manual_left_frame.pack(side=LEFT, expand=1, fill=X)
	self.nb.pack(side=TOP, expand=1, fill=X)
	self.ne.pack(side=BOTTOM, expand=1, fill=X)
	self.he.pack(side=TOP, expand=1, fill=X)
	self.hb.pack(side=TOP, expand=1, fill=X)
	self.fe.pack(side=TOP, expand=1, fill=X)
	self.fb.pack(side=TOP, expand=1, fill=X)

	#
	# Set the initial GUI state based on prefs
	self.register_prefs_UI()
	if grailutil.pref_or_getenv('no_proxy_enabled', type_name='Boolean'):
	    self.no_proxy_enabled.set(1)
	self.no_switch()
	if grailutil.pref_or_getenv('manual_proxy_enabled', type_name='Boolean'):
	    self.manual_proxy_enabled.set(1)
	self.manual_switch()
	self.ftp_entry_toggle()
	self.http_entry_toggle()
	self.no_proxy_entry_toggle()
	

    def register_prefs_UI(self):
	"""Associate the UI widgets with the Preferences variables."""

	self.RegisterUI('proxies', 'no_proxy_enabled', 'Boolean',
			self.no_proxy_enabled.get,
			self.no_proxy_enabled.set)

	self.RegisterUI('proxies', 'manual_proxy_enabled', 'Boolean',
			self.manual_proxy_enabled.get,
			self.manual_proxy_enabled.set)

	self.RegisterUI('proxies', 'no_proxy', 'string',
			self.ne.get, self.widget_set_func(self.ne))
	self.RegisterUI('proxies', 'ftp_proxy', 'string',
			self.fe.get, self.widget_set_func(self.fe))
	self.RegisterUI('proxies', 'http_proxy', 'string',
			self.he.get, self.widget_set_func(self.he))


    def no_switch(self):
	""" Set the state of the No Proxy Configuration controls
	to DISABLED if the Checkbutton is no set."""
	
	if self.no_proxy_enabled.get():
	    self.nb_state.set(1)
	    self.nb.config(state=NORMAL)
	    self.ne.config(state=NORMAL)
	else:
	    self.nb_state.set(0)
	    self.nb.config(state=DISABLED)
	    self.ne.config(state=DISABLED)
	
    def manual_switch(self):
	""" Set the state of the Manual Proxy Configuration controls
	to DISABLED if the Checkbutton is no set."""

	if self.manual_proxy_enabled.get():
	    self.he.config(state=NORMAL)
	    self.fe.config(state=NORMAL)
	    self.hb.config(state=NORMAL)
	    self.fb.config(state=NORMAL)
	    self.hb_state.set(0)
	    self.fb_state.set(0)
	    self.he.config(state=DISABLED)
	    self.fe.config(state=DISABLED)
       	    #
	    # Re-enable No Proxy
	    self.no.config(state=NORMAL)
	else:
	    self.he.config(state=DISABLED)
	    self.fe.config(state=DISABLED)
	    self.hb.config(state=DISABLED)
	    self.fb.config(state=DISABLED)
	    self.hb_state.set(0)
	    self.fb_state.set(0)
	    self.he.config(state=DISABLED)
	    self.fe.config(state=DISABLED)
	    #
	    # We also disable No Proxy
	    self.no_proxy_enabled.set(0)
	    self.nb_state.set(0)
	    self.nb.config(state=DISABLED)
	    self.ne.config(state=DISABLED)
	    self.no.config(state=DISABLED)
	    
    def ftp_entry_toggle(self):
	"""Enable and disable the FTP entry field."""

	if self.fb_state.get():
	    self.fe.config(state=NORMAL)
	else:
	    self.fe.config(state=DISABLED)
	
    def http_entry_toggle(self):
	"""Enable and disable the HTTP entry field."""
	
	if self.hb_state.get():
	    self.he.config(state=NORMAL)
	else:
	    self.he.config(state=DISABLED)
	
    def no_proxy_entry_toggle(self):
	"""Enable and disable the No Proxy entry field."""

	if self.nb_state.get():
	    self.ne.config(state=NORMAL)
	else:
	    self.ne.config(state=DISABLED)


