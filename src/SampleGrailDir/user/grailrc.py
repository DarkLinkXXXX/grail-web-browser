# Grail initialization file


import GrailRemoteControl
from __main__ import app

# remote control of Grail, only implements loading a URL and loading a
# URL in a new browser window.
def do_load(uri, in_new_window=None):
    # get a reference to one of the browsers in the application
    browsers = app.browsers
    if len(browsers) > 0: b = browsers[-1]
    else: return
    # create a new browser toplevel?
    if in_new_window:
	import Browser
	b = Browser.Browser(b.master, app)
    # tell it to load the URL
    b.load(uri)

def set_up_callbacks():
    sockfile = '/tmp/.grail-bwarsaw/:0'
    rc = GrailRemoteControl.RemoteControl(sockfile)
    # callback commands
    def _load(cmdstr, argstr): do_load(argstr)
    def _loadnew(cmdstr, argstr): do_load(argstr, 1)
    # register
    rc.register('LOAD', _load)
    rc.register('LOADNEW', _loadnew)
    try:
	rc.begin()
    except GrailRemoteControl.RC_SOCKET_EXISTS:
	# socket exists.  no big deal, just wax it
	import os
	os.unlink(sockfile)
	rc.begin()

set_up_callbacks()
