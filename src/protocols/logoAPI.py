"""logo: URI scheme handler."""

from nullAPI import null_access

class logo_access(null_access):

    def __init__(self, url, method, params):
	null_access.__init__(self, url, method, params)
	import logodata
	if not logodata.dir.has_key(url):
	    raise IOError, "no logo file %s" % url
	self.data = logodata.dir[url]
	self.offset = 0

    def getmeta(self):
	null_access.getmeta(self)
	return 200, "OK", {}

    def getdata(self, maxbytes):
	print "getdata", maxbytes
	data = self.data[self.offset : self.offset + maxbytes]
	print len(data)
	self.offset = self.offset + len(data)
	if not data:
	    return null_access.getdata(self, maxbytes)
	else:
	    return data
