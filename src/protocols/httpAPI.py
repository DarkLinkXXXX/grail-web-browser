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
import select
import regex
import StringIO


# Search for blank line following HTTP headers
endofheaders = regex.compile("\n[ \t]*\r?\n")


# Stages
META = 'meta'
DATA = 'data'
DONE = 'done'


class MyHTTP(httplib.HTTP):

    def putrequest(self, request, selector):
	self.selector = selector
	httplib.HTTP.putrequest(self, request, selector)

    def getreply(self, file):
	self.file = file
	line = self.file.readline()
	if self.debuglevel > 0: print 'reply:', `line`
	if replyprog.match(line) < 0:
	    # Not an HTTP/1.0 response.  Fall back to HTTP/0.9.
	    # Push the data back into the file.
	    self.file.seek(-len(line), 1)
	    self.headers = {}
	    c_type, c_encoding = __main__.app.guess_type(self.selector)
	    if c_encoding:
		self.headers['content-encoding'] = c_encoding
	    # HTTP/0.9 sends HTML by default
	    self.headers['content-type'] = c_type or "text/html"
	    return 200, "OK", self.headers
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
	if data:
	    assert(method=="POST")
	else:
	    assert(method in ("GET", "POST"))
	if type(resturl) == type(()):
	    host, selector = resturl	# For proxy interface
	else:
	    host, selector = splithost(resturl)
	if not host:
	    raise IOError, "no host specified in URL"
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
	self.readahead = ""
	self.stage = META
	self.line1seen = 0

    def close(self):
	if self.h:
	    self.h.close()
	self.h = None

    def pollmeta(self):
	assert(self.stage == META)
	sock = self.h.sock
	if not select.select([sock.fileno()], [], [], 0)[0]:
	    return "waiting for metadata", 0
	new = sock.recv(1024)
	if not new:
	    return "EOF in metadata", 1
	self.readahead = self.readahead + new
	if '\n' not in new:
	    return "receiving metadata", 0
	if not self.line1seen:
	    i = string.find(self.readahead, '\n')
	    if i < 0:
		return "receiving metadata", 0
	    self.line1seen = 1
	    line = self.readahead[:i+1]
	    if replyprog.match(line) < 0:
		return "received non-HTTP metadata", 1
	i = endofheaders.search(self.readahead)
	if i >= 0:
	    return "received metadata", 1
	return "receiving metadata", 0

    def getmeta(self):
	assert(self.stage == META)
	file = StringIO.StringIO(self.readahead)
	errcode, errmsg, headers = self.h.getreply(file)
	self.stage = DATA
	self.readahead = file.read()
	return errcode, errmsg, headers

    def polldata(self):
	assert(self.stage == DATA)
	if self.readahead:
	    return "reading readahead data", 1
	return ("waiting for data",
		len(select.select([self.fileno()], [], [], 0)[0]))

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
