# Copyright CNRI, licensed under GRAIL license agreement obtained from
# "http://grail.cnri.reston.va.us/LICENSE-0.3", or found in file "LICENSE".

"""grail: URI scheme handler."""

import grailutil
from nullAPI import null_access

class grail_access(null_access):

    def __init__(self, url, method, params):
	null_access.__init__(self, url, method, params)
	self.url = "file:" + grailutil.which(url)

    def getmeta(self):
	null_access.getmeta(self)	# assert, state change
	return 301, "Redirected", {'location': self.url}
