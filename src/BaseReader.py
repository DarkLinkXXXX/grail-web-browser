"""Base reader class -- read from a URL in the background."""

import sys
from Tkinter import *


# Default tuning parameters
# BUFSIZE = 8*1024			# Buffer size for api.getdata()
BUFSIZE = 512				# Smaller size for better response
SLEEPTIME = 100				# Milliseconds between regular checks

class BaseReader:

    """Base reader class -- read from a URL in the background.

    Given an API object, poll it until it completes or an
    unrecoverable error occurs.

    Derived classes are supposed to override the handle_*() methods to
    do something meaningful.

    The sequence of calls made to the stop and handle_* functions can
    be expressed by a regular expression:

    (meta data* stop (eof | error) | stop handle_error)

    """

    # Tuning parameters
    bufsize = BUFSIZE
    sleeptime = SLEEPTIME

    def __init__(self, browser, api):
	self.browser = browser
	self.api = api

	self.callback = self.checkmeta
	self.fno = self.api.fileno()
	if TkVersion == 4.0 and sys.platform == 'irix5':
	    if self.fno >= 20: self.fno = -1 # XXX for SGI Tk OPEN_MAX bug

	self.browser.addreader(self)

	if self.fno >= 0:
	    tkinter.createfilehandler(
		self.fno, tkinter.READABLE, self.checkapi)
	else:
##	    print "No fileno() -- check every 100 ms"
	    self.checkapi_regularly()

    def __repr__(self):
	return "%s(%s)" % (self.__class__.__name__, self.api)

    def kill(self):
	self.stop()
	self.handle_error(-1, "Killed", {})

    def stop(self):
	if self.browser:
	    self.browser.rmreader(self)
	    self.browser = None

	if self.fno >= 0:
	    fno = self.fno
	    self.fno = -1
	    tkinter.deletefilehandler(fno)

	self.callback = None

	if self.api:
	    self.api.close()
	    self.api = None

    def checkapi_regularly(self):
	if not self.callback:
##	    print "*** checkapi_regularly -- too late ***"
	    return
	self.callback()
	if self.callback:
	    self.browser.root.after(self.sleeptime, self.checkapi_regularly)

    def checkapi(self, *args):
	if not self.callback:
	    print "*** checkapi -- too late ***"
	    if self.fno >= 0:
		fno = self.fno
		self.fno = -1
		tkinter.deletefilehandler(fno)
	    return
	self.callback()			# Call via function pointer

    def checkmeta(self):
	message, ready = self.api.pollmeta()
	if ready:
	    self.getapimeta()

    def checkdata(self):
	message, ready = self.api.polldata()
	if ready:
	    self.getapidata()

    def getapimeta(self):
	errcode, errmsg, headers = self.api.getmeta()
	self.callback = self.checkdata
	if headers.has_key('content-type'):
	    content_type = headers['content-type']
	else:
	    content_type = None
	if headers.has_key('content-encoding'):
	    content_encoding = headers['content-encoding']
	else:
	    content_encoding = None
	self.content_type = content_type
	self.content_encoding = content_encoding
	self.handle_meta(errcode, errmsg, headers)

    def getapidata(self):
	data = self.api.getdata(self.bufsize)
	if not data:
	    self.stop()
	    self.handle_eof()
	    return
	self.handle_data(data)

    def geteverything(self):
	if self.api:
	    if self.callback == self.checkmeta:
		self.getapimeta()
	    while self.api:
		self.getapidata()

    # Derived classes are expected to override the following methods

    def handle_meta(self, errcode, errmsg, headers):
	# May call self.stop()
	if errcode != 200:
	    self.stop()
	    self.handle_error(errcode, errmsg, headers)

    def handle_data(self, data):
	# May call self.stop()
	pass

    def handle_error(self, errcode, errmsg, headers):
	# Called after self.stop() has been called
	pass

    def handle_eof(self):
	# Called after self.stop() has been called
	pass
