from assert import assert

META, DATA, DONE = 'META', 'DATA', 'DONE'

class null_access:

    def __init__(self, url, method, params):
	self.state = META

    def pollmeta(self):
	assert(self.state == META)
	return "Ready", 1

    def getmeta(self):
	assert(self.state == META)
	self.state = DATA
	return 204, "No content", {}

    def polldata(self):
	assert(self.state == DATA)
	return "Ready", 1

    def getdata(self, maxbytes):
	assert(self.state == DATA)
	self.state = DONE
	return ""

    def close(self):
	pass
