from assert import assert

META, DATA, DONE = 'META', 'DATA', 'DONE'

class file_access:

    def __init__(self, url, method, params):
	self.fp = open(url)		# May raise IOError!
	self.state = META

    def pollmeta(self):
	assert(self.state == META)
	return "Ready", 1

    def getmeta(self):
	assert(self.state == META)
	self.state = DATA
	return 200, "OK", {}

    def polldata(self):
	assert(self.state == DATA)
	return "Ready", 1

    def getdata(self, maxbytes):
	assert(self.state == DATA)
	data = self.fp.read(maxbytes)
	if not data:
	    self.state = DONE
	return data

    def close(self):
	fp = self.fp
	self.fp = None
	if fp:
	    fp.close()
