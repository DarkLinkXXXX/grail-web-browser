"""Provisional HTTP interface using the new protocol API.

XXX This was hacked together in an hour si I would have something to
test ProtocolAPI.py.  Especially the way it uses knowledge about the
internals of httplib.HTTP is disgusting (but then, so would editing
the source of httplib.py be :-).

XXX Main deficiencies:

- poll*() always returns ready
- should read the headers more carefully (no blocking)
- (could even *write* the headers more carefully)
- should poll the connection making part too

"""


import string
import httplib
from urllib import splithost
import mimetools
from assert import assert
from httplib import replyprog
import __main__


# Stages
META = 'meta'
DATA = 'data'
DONE = 'done'


class MyHTTP(httplib.HTTP):

    def getreply(self):
	# Use unbuffered file so we can use the raw socket later on;
	# don't zap the socket
	self.file = self.sock.makefile('r', 0)
	line = self.file.readline()
	if self.debuglevel > 0: print 'reply:', `line`
	if replyprog.match(line) < 0:
	    # Not an HTTP/1.0 response.  Fall back to HTTP/0.9.
	    self.headers = {}
	    return -1, line, self.headers
	errcode, errmsg = replyprog.group(1, 2)
	errcode = string.atoi(errcode)
	errmsg = string.strip(errmsg)
	self.headers = mimetools.Message(self.file, 0)
	return errcode, errmsg, self.headers

    def close(self):
	if self.file:
	    self.file.close()
	if self.sock:
	    self.sock.close()
	self.file = None
	self.sock = None


class http_access:

    def __init__(self, resturl, method, params, data=None):
	grailversion = __main__.__version__
	if data is not None:
	    assert(method=="POST")
	else:
	    assert(method=="GET")
	if type(resturl) == type(()):
	    host, selector = resturl	# For proxy interface
	else:
	    host, selector = splithost(resturl)
	assert(host!="")
	i = string.find(host, '@')
	if i >= 0:
	    user_passwd, host = host[:i], host[i+1:]
	else:
	    user_passwd = None
	if user_passwd:
	    import base64
	    auth = string.strip(base64.encodestring(user_passwd))
	else:
	    auth = None
	self.h = MyHTTP(host)
##	self.h.set_debuglevel(2)
	self.h.putrequest(method, selector)
	self.h.putheader('User-agent', grailversion)
	if auth:
	    self.h.putheader('Authorization', 'Basic %s' % auth)
	for key, value in params.items():
	    if key[:1] != '.':
		self.h.putheader(key, value)
	self.h.endheaders()
	if data:
	    self.h.send(data)
	self.stage = META

    def close(self):
	if self.h:
	    self.h.close()
	self.h = None

    def pollmeta(self):
	assert(self.stage == META)
	return "waiting for response", 1

    def getmeta(self):
	assert(self.stage == META)
	errcode, errmsg, headers = self.h.getreply()
	self.stage = DATA
	self.readahead = None
	if errcode == -1:
	    self.readahead = errmsg
	return errcode, errmsg, headers

    def polldata(self):
	assert(self.stage == DATA)
	if self.readahead:
	    return "reading readahead data", 1
	return "waiting for data", 1

    def getdata(self, maxbytes):
	assert(self.stage == DATA)
	if self.readahead:
	    data = self.readahead
	    self.readahead = None
	    return data
	data = self.h.sock.recv(maxbytes)
	if not data:
	    self.stage = DONE
	    self.close()
	return data

    def fileno(self):
	return self.h.sock.fileno()


# To test this, use ProtocolAPI.test()
