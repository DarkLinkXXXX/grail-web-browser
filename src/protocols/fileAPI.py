from assert import assert
import os

META, DATA, DONE = 'META', 'DATA', 'DONE'

LISTING_HEADER = """<HTML>
<HEAD>
<BASE HREF="%(url)s">
<TITLE>Local Directory: %(url)s</TITLE>
</HEAD>
<BODY>
<H1>Local Directory: %(pathname)s</H1>
<PRE>"""

LISTING_TRAILER = """</PRE>
</BODY>
"""

LISTING_PATTERN = """\
^\([-a-z][-a-z][-a-z][-a-z][-a-z][-a-z][-a-z][-a-z][-a-z][-a-z]\)\
\([ \t]+.*[ \t]+\)\([^ \t]+\)$"""

class file_access:

    def __init__(self, url, method, params):
	from urllib import unquote
	self.url = url
	self.pathname = unquote(self.url)
	self.method = method
	self.params = params
	self.headers = {}
	if os.path.isdir(self.pathname):
	    self.format_directory()
	else:
	    self.fp = open(self.pathname) # May raise IOError!
	    from __main__ import app
	    ctype, cencoding = app.guess_type(self.pathname)
	    if ctype: self.headers['content-type'] = ctype
	    if cencoding: self.headers['content-encoding'] = cencoding
	self.state = META

    def pollmeta(self):
	assert(self.state == META)
	return "Ready", 1

    def getmeta(self):
	assert(self.state == META)
	self.state = DATA
	return 200, "OK", self.headers

    def polldata(self):
	assert(self.state == DATA)
	return "Ready", 1

    def getdata(self, maxbytes):
	assert(self.state == DATA)
	data = self.fp.read(maxbytes)
	if not data:
	    self.state = DONE
	return data

    def fileno(self):
	try:
	    return self.fp.fileno()
	except AttributeError:
	    return -1

    def close(self):
	fp = self.fp
	self.fp = None
	if fp:
	    fp.close()

    def format_directory(self):
	# XXX Unixism
	if self.url and self.url[-1] != '/':
	    self.url = self.url + '/'
	fp = os.popen("ls -l -a %s 2>&1" % self.pathname, "r")
	lines = fp.readlines()
	fp.close()
	import StringIO
	import regex
	from urllib import quote
	from urlparse import urljoin
	import regsub
	def escape(s, regsub=regsub):
	    if not s: return ""
	    s = regsub.gsub('&', '&amp;', s) # Must be done first
	    s = regsub.gsub('<', '&lt;', s)
	    s = regsub.gsub('>', '&gt;', s)
	    return s
	prog = regex.compile(self.listing_pattern)
	data = self.listing_header % {'url': self.url,
				      'pathname': escape(self.pathname)}
	for line in lines:
	    if line[-1] == '\n': line = line[:-1]
	    if prog.match(line) < 0:
		line = escape(line) + '\n'
		data = data + line
		continue
	    mode, middle, name = prog.group(1, 2, 3)
	    rawname = name
	    [mode, middle, name] = map(escape, [mode, middle, name])
	    href = urljoin(self.url, quote(rawname))
	    if len(mode) == 10 and mode[0] == 'd' or name[-1:] == '/':
		if name[-1:] != '/':
		    name = name + '/'
		if href[-1:] != '/':
		    href = href + '/'
	    line = '%s%s<A HREF="%s">%s</A>\n' % (
		mode, middle, escape(href), name)
	    data = data + line
	data = data + self.listing_trailer
	self.fp = StringIO.StringIO(data)
	self.headers['content-type'] = 'text/html'

    listing_header = LISTING_HEADER
    listing_trailer = LISTING_TRAILER
    listing_pattern = LISTING_PATTERN
