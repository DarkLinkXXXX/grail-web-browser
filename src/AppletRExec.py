"""Restricted execution for Applets."""


import SafeDialog
import SafeTkinter
import os
from rexec import RExec, RHooks
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
	if is_url(p):
	    if mode not in ('r', 'rb'):
		raise IOError, "Can't open URL for writing"
	    return urllib.urlopen(p)
	else:
	    return open(p, mode, buf)


class AppletRExec(RExec):

    def __init__(self, hooks=None, verbose=1):
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
	    return RExec.r_open(self, file, mode, buf)
	head, tail = os.path.split(file)
	tempdir = tempfile.gettempdir()
	if head != tempdir:
	    raise IOError, "only files in %s are writable" % tempdir
	return open(os.path.join(tempdir, tail), mode, buf)

    # This is temporary until it is part of the library
    def r_unload(self, m):
        return self.importer.unload(m)
