# This class provides the structure for a generalized remote control
# operation of Grail.  You can instantiate and populate this class in
# your $GRAILDIR/user/grailrc.py file.  By doing so, you can allow
# remote control of any of Grail's functionality.
#
# On security: there is no real security model here.  You need to use
# your own head about this.  This class operates in unprotected mode,
# so be very careful what you open up.  Unix domain sockets are used
# so only the Grail user on the local host should be able to send
# commands to this interface.  Still how secure is that?
#
# This module essentially opens the socket and registers it with Tk so
# when data is readable on it, registered callbacks are executed.
# This is a really simple minded string based protocol, with a
# synchronous server model.  It's also only one-way.  Right now, it
# doesn't send any data back to the client.  Commands are limited to
# 1024 bytes.

import tempfile
import os
import socket
import regex
import string
import tkinter
from grailutil import *

# The file structure.  Modeled after X11
TMPDIR = tempfile.gettempdir()
USER = getenv('USER') or getenv('LOGNAME')
XDISPLAY = getenv('DISPLAY') or ':0'
RC_FILENAME = os.path.join(TMPDIR,
			   os.path.join('.grail-unix',
					'%s-%s' % (USER, XDISPLAY)))

# errors
RC_SOCKET_EXISTS = 'RC_SOCKET_EXISTS'
RC_NO_FILENO = 'RC_NO_FILENO'
RC_BAD_COMMAND_FORMAT = 'RC_BAD_COMMAND_FORMAT'
RC_NO_COMMAND = 'RC_NO_COMMAND'



class RemoteControl:
    def __init__(self, path=RC_FILENAME):
	# register a destruction handler with the Grail Application object
	from __main__ import app
	self._app = app
	app.register_on_exit(self._close)
	# calculate the socket's filename
	self._path = path
	self._fileno = None
	self._socket = None
	# Don't create the socket now, because we want to allow
	# clients of this class to register callbacks for commands
	# first.
	self._cbdict = {}
	self._cmdre = regex.compile('\([^ \t]+\)\(.*\)')

    def begin(self):
	"""Begin listening for remote control commands.

	You should have registered all your callbacks before calling
	this method, but that's not required.
	"""
	# for security, create the file structure
	head, self._filename = os.path.split(self._path)
	dirhier = []
	while head and not os.path.isdir(head):
	    head, t = os.path.split(head)
	    dirhier.insert(0, t)
	for dir in dirhier:
	    head = os.path.join(head, dir)
	    os.mkdir(head, 0700)
	self._filename = self._path
	# What do we do with multiple Grail processes?  Which one do
	# we remote control?  That's a higher level decision.
	if os.path.exists(self._filename):
	    raise RC_SOCKET_EXISTS, \
		  'Grail remote control file already in use: ' + self._filename
	# create the FIFO object
	s = self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
	s.bind(self._filename)
	s.listen(1)
	# register with Tk
	self._fileno = s.fileno()
	if self._fileno >= 0:
	    tkinter.createfilehandler(
		self._fileno, tkinter.READABLE, self._dispatch)
	else:
	    raise RC_NO_FILENO, 'Could not get fileno for Tk'

    def register(self, cmdstr, callback):
	"""Register command string, callback function pairs.

	Command format is 'CMDSTR ARGS' where CMDSTR is some command
	string as defined by the client of this class.  ARGS is
	anything that follows, and is command specific.

	Format of the callback method is: callback(cmdstr, argstr).
	More than one callback can be defined for a command, and they
	are called in the order they are registered in.  Note that any
	exceptions raised in the callback are passed straight up
	through to Grail.
	"""
	if self._cbdict.has_key(cmdstr):
	    cblist = self._cbdict[cmdstr]
	    cblist.append(callback)
	else:
	    self._cbdict[cmdstr] = [callback]

    def unregister(self, cmdstr, callback=None):
	"""Unregister a command string, callback mapping.

	If callback is None (the default), this unregisters all
	callbacks associated with a command.
	"""
	if self._cbdict.has_key(cmdstr):
	    cblist = self._cbdict[cmdstr]
	    if callback and callback in cblist:
		cblist.remove(callback)
	    else:
		del self._cbdict[cmdstr]

    ## private methods

    def _close(self):
	if self._fileno: tkinter.deletefilehandler(self._fileno)
	if self._filename: os.unlink(self._filename)

    def _dispatch(self, *args):
	conn, addr = self._socket.accept()
	rawdata = conn.recv(1024)
	# strip off the command string
	string.strip(rawdata)
	if self._cmdre.match(rawdata) < 0:
	    raise RC_BAD_COMMAND_FORMAT, 'Bad remote command: ' + rawdata
	# extract the command and args strings
	command = string.strip(self._cmdre.group(1))
	argstr = string.strip(self._cmdre.group(2))
	# look up the command string
	if not self._cbdict.has_key(command):
	    raise RC_NO_COMMAND, 'No callbacks for command: ' + command
	cblist = self._cbdict[command]
	# call all callbacks in list
	for cb in cblist: cb(command, argstr)
