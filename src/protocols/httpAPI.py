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


class _socketfile:

    """Helper class to simulate file object with access to its buffer."""

    # Code copied from Lib/mac/socket.py

    def __init__(self, sock, rw, bs):
	if rw not in ('r', 'w'): raise _myerror, "mode must be 'r' or 'w'"
	self.sock = sock
	self.rw = rw
	self.bs = bs
	self.buf = ''

    def read(self, length = -1):
	if length < 0:
	    length = 0x7fffffff
	while len(self.buf) < length:
	    new = self.sock.recv(64)
	    if not new:
		break
	    self.buf = self.buf + new
	rv = self.buf[:length]
	self.buf = self.buf[length:]
	return rv

    def readline(self):
	while not '\n' in self.buf:
	    new = self.sock.recv(64)
	    if not new:
		break
	    self.buf = self.buf + new
	if not '\n' in self.buf:
	    rv = self.buf
	    self.buf = ''
	else:
	    i = string.index(self.buf, '\n')
	    rv = self.buf[:i+1]
	    self.buf = self.buf[i+1:]
	return rv

    def readlines(self):
	list = []
	line = self.readline()
	while line:
	    list.append(line)
	    line = self.readline()
	return list

    def write(self, buf):
	BS = self.bs
	if len(buf) >= BS:
	    self.flush()
	    self.sock.send(buf)
	elif len(buf) + len(self.buf) >= BS:
	    self.flush()
	    self.buf = buf
	else:
	    self.buf = self.buf + buf

    def writelines(self, list):
	for line in list:
	    self.write(line)

    def flush(self):
	if self.buf and self.rw == 'w':
	    self.sock.send(self.buf)
	    self.buf = ''

    def close(self):
	self.flush()
	##self.sock.close()
	del self.sock


class MyHTTP(httplib.HTTP):

    def putrequest(self, request, selector):
	self.selector = selector
	httplib.HTTP.putrequest(self, request, selector)

    def getreply(self):
	# Use unbuffered file so we can use the raw socket later on;
	# don't zap the socket
	self.file = _socketfile(self.sock, 'r', 0)
	line = self.file.readline()
	if self.debuglevel > 0: print 'reply:', `line`
	if replyprog.match(line) < 0:
	    # Not an HTTP/1.0 response.  Fall back to HTTP/0.9.
	    self.headers = {}
	    c_type, c_encoding = __main__.app.guess_type(self.selector)
	    if c_encoding:
		self.headers['content-encoding'] = c_encoding
	    # HTTP/0.9 sends HTML by default
	    self.headers['content-type'] = c_type or "text/html"
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
	self.readahead = self.h.file.buf
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
