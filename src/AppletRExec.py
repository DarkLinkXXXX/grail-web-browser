"""Restricted execution for Applets."""


import SafeDialog
import SafeTkinter
import os
from rexec import RExec, RHooks
import string
import sys
import tempfile
import types
import urllib
import urlparse


def is_url(p):
    u = urlparse.urlparse(p)
    return u[0] or u[1]


class AppletRHooks(RHooks):

    def path_join(self, p1, p2):
	if is_url(p1) or is_url(p2):
	    return urlparse.urljoin(p1, p2)
	else:
	    return os.path.join(p1, p2)

    def openfile(self, p, mode='r', buf=-1):
	# Only used to read modules
	if is_url(p):
	    return self.openurl(p, mode, buf)
	else:
	    return open(p, mode, buf)

    def openurl(self, p, mode='r', buf=-1):
	if mode not in ('r', 'rb'):
	    raise IOError, "Can't open URL for writing"
	app = self.rexec.app
	if not app:
	    # Fall back for test mode
	    return urllib.urlopen(p)
	# Always specify reload since modules are already cached --
	# when we get here it must either be the first time for
	# this module or the user has requested to reload the page.
	api = self.rexec.app.open_url(p, 'GET', {}, reload=1)
	errcode, errmsg, params = api.getmeta()
	if errcode != 200:
	    api.close()
	    raise IOError, errmsg
	return PseudoFile(api)


class PseudoFile:

    # XXX Is this safe?
    # XXX Is this sufficient?

    def __init__(self, api):
	self.api = api
	self.buf = ''
	self.done = 0

    def close(self):
	api = self.api
	self.api = self.buf = self.done = None
	if api:
	    api.close()

    def read(self, n=-1):
	if n < 0:
	    n = sys.maxint
	while len(self.buf) < n and not self.done:
	    self.fill(min(n - len(self.buf), 1024*8))
	data, self.buf = self.buf[:n], self.buf[n:]
	return data

    def readlines(self):
	list = []
	while 1:
	    line = self.readline()
	    if not line: break
	    list.append(line)
	return list

    def readline(self):
	while '\n' not in self.buf and not self.done:
	    self.fill()
	i = string.find(self.buf, '\n')
	if i < 0:
	    i = len(self.buf)
	else:
	    i = i+1
	data, self.buf = self.buf[:i], self.buf[i:]
	return data

    def fill(self, n = 512):
	data = self.api.getdata(n)
	if data:
	    self.buf = self.buf + data
	else:
	    self.done = 1


class AppletRExec(RExec):

    def __init__(self, hooks=None, verbose=1, app=None):
	self.app = app
	if not hooks: hooks = AppletRHooks(self, verbose)
	RExec.__init__(self, hooks, verbose)
	self.modules['Dialog'] = SafeDialog
	self.modules['Tkinter'] = SafeTkinter
	self.save_files()
	self.set_files()

    def set_urlpath(self, url):
	self.reset_urlpath()
	path = self.modules['sys'].path
	path.append(url)

    def reset_urlpath(self):
	path = self.modules['sys'].path
	path[:] = filter(lambda x: not is_url(x), path)

    def make_initial_modules(self):
	RExec.make_initial_modules(self)
	self.make_al()
	self.make_socket()
	self.make_sunaudiodev()
	self.make_types()
 
    def make_al(self):
	try:
	    import al
	except ImportError:
	    return
	m = self.copy_except(al, ())
 
    def make_socket(self):
	try:
	    import socket
	except ImportError:
	    return
	m = self.copy_except(socket, ('fromfd',))

    def make_sunaudiodev(self):
	try:
	    import sunaudiodev
	except ImportError:
	    return
	m = self.copy_except(sunaudiodev, ())

    def make_types(self):
	m = self.copy_except(types, ())

    def r_open(self, file, mode='r', buf=-1):
	if not (type(file) == type('') == type(mode)):
	    raise TypeError, "open(): file and mode must be strings"
	if mode in ('r', 'rb'):
	    if is_url(file):
		return self.hooks.openurl(file)
	    return RExec.r_open(self, file, mode, buf)
	head, tail = os.path.split(file)
	tempdir = tempfile.gettempdir()
	if head != tempdir:
	    raise IOError, "only files in %s are writable" % tempdir
	return open(os.path.join(tempdir, tail), mode, buf)
