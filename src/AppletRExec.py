"""Restricted execution for Applets."""


from rexec import RExec, RHooks
import SafeDialog
import SafeTkinter
import urlparse
import urllib
import os
import socket
import types


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

    def set_urlpath(self, url):
	self.reset_urlpath()
	path = self.modules['sys'].path
	path.append(url)

    def reset_urlpath(self):
	path = self.modules['sys'].path
	path[:] = filter(lambda x: not is_url(x), path)

    def make_initial_modules(self):
	self.make_main()
	self.make_osname()
	self.make_socket()
	self.make_types()

    def make_socket(self):
	m = self.copy_except(socket, ())

    def make_types(self):
	m = self.copy_except(types, ())
