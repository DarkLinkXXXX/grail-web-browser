"""Provisional FTP interface using the new protocol API.

XXX Main deficiencies:

- poll*() always returns ready
- should read the headers more carefully (no blocking)
- (could even *write* the headers more carefully)
- should poll the connection making part too

"""


import string
import ftplib
from urllib import splithost, splitport, splituser, splitpasswd, splitattr
import mimetools
from assert import assert
import socket
from urllib import ftperrors, unquote


# Stages
META = 'meta'
DATA = 'data'
DONE = 'done'


ftpcache = {}			# XXX Ouch!  A global!


class ftp_access:

	def __init__(self, url, method, params):
		assert(method == 'GET')
		host, path = splithost(url)
		if not host: raise IOError, ('ftp error', 'no host given')
		host, port = splitport(host)
		user, host = splituser(host)
		if user: user, passwd = splitpasswd(user)
		else: passwd = None
		host = socket.gethostbyname(host)
		if not port:
			port = ftplib.FTP_PORT
		path, attrs = splitattr(path)
		dirs = string.splitfields(path, '/')
		dirs, file = dirs[:-1], dirs[-1]
		if dirs and not dirs[0]: dirs = dirs[1:]
		key = (user, host, port, string.joinfields(dirs, '/'))
		try:
			if not ftpcache.has_key(key):
				ftpcache[key] = []
			if not file: type = 'D'
			else: type = 'I'
			for attr in attrs:
				attr, value = splitvalue(attr)
				if string.lower(attr) == 'type' and \
				   value in ('a', 'A', 'i', 'I', 'd', 'D'):
					type = string.upper(value)
			candidates = ftpcache[key]
			for cand in candidates:
				if not cand.busy():
					break
			else:
				cand = ftpwrapper(user, passwd,
						  host, port, dirs)
				candidates.append(cand)
			# XXX Need to clean the cache every once in a while
			self.cand = cand
			self.sock = cand.retrfile(file, type)
		except ftperrors(), msg:
			raise IOError, ('ftp error', msg)
		self.state = META
	
	def pollmeta(self):
		assert(self.state == META)
		return "Ready", 1
	
	def getmeta(self):
		assert(self.state == META)
		self.state = DATA
		# XXX Ought to return the Content-type
		return 200, "OK", {}
	
	def polldata(self):
		assert(self.state == DATA)
		return "Ready", 1
	
	def getdata(self, maxbytes):
		assert(self.state == DATA)
		data = self.sock.recv(maxbytes)
		if not data:
			self.state = DONE
		return data
	
	def close(self):
		sock = self.sock
		cand = self.cand
		self.sock = None
		self.cand = None
		if sock:
			sock.close()
		if cand:
			cand.done()


class ftpwrapper:

	"""Helper class for cache of open FTP connections"""

	def __init__(self, user, passwd, host, port, dirs):
		self.user = unquote(user or '')
		self.passwd = unquote(passwd or '')
		self.host = host
		self.port = port
		self.dirs = []
		for dir in dirs:
			self.dirs.append(unquote(dir))
		self.reset()
	
	def __del__(self):
		self.done()
		self.quit()

	def reset(self):
		self.conn = None
		self.ftp = ftplib.FTP()
		self.ftp.connect(self.host, self.port)
		self.ftp.login(self.user, self.passwd)
		for dir in self.dirs:
			self.ftp.cwd(dir)

	def busy(self):
		return self.conn and 1

	def done(self):
		conn = self.conn
		self.conn = None
		if conn:
			conn.close()
			self.ftp.voidresp()

	def retrfile(self, file, type):
		if type in ('d', 'D'): cmd = 'TYPE A'; isdir = 1
		else: cmd = 'TYPE ' + type; isdir = 0
		try:
			self.ftp.voidcmd(cmd)
		except ftplib.all_errors:
			self.reset()
			self.ftp.voidcmd(cmd)
		conn = None
		if file and not isdir:
			try:
				cmd = 'RETR ' + file
				conn = self.ftp.transfercmd(cmd)
				# XXX Should guess filetype from extensions
			except ftplib.error_perm, reason:
				if reason[:3] != '550':
					raise IOError, ('ftp error', reason)
		if not conn:
			# Try a directory listing
			# XXX Should convert to HTML
			if file: cmd = 'LIST ' + file
			else: cmd = 'LIST'
			conn = self.ftp.transfercmd(cmd)
		self.conn = conn
		return conn


# To test this, use ProtocolAPI.test()
