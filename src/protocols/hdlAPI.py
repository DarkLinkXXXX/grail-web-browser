# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""CNRI handle protocol extension.

This module glues the backend CNRI handle client resolution module in
hdllib.py to the Grail 0.2 URI protocol API.  Currently we are only
interested in URL type handles, so we can get away semantically with
returning an HTTP-style relocation error to the browser for the
resolved handle (if the handle resolves to a single URL), or to
generating a piece of HTML which lets the user choose one (if it
resolves to multiple URLs).

XXX Problems:

	1. hdllib.py currently only supports the older handle
	   protocol.  Specifically, it doesn't support dynamic
	   downloading of the hash table, and consequently it doesn't
	   support local handle servers.  This isn't a big deal
	   currently because no local handle servers have been
	   deployed, and the global system is backward compatible with
	   the old protocol.  (We aren't even entirely sure whether
	   the protocol has actually changed.)

	2. I don't think it handles continuation packets correctly.
	   This isn't a big deal since in this context, we're only
	   concerned with URL type values, which are smaller than the
	   packet size.  (This is really an issue with hdllib.py.)

	3. Issuing a 302 relocate isn't the proper thing to do in the
	   long term, because it forces the user back into URL space.
	   So, for example, the user will naturally keep the resolved
	   URL on her bookmarks, instead of the original handle.
	   However, for backward compatibility with relative links, we
	   need to define relative-handle semantics.  We're working
	   with the CNRI handle group to define this and we'll be
	   experimenting with solutions in the future.  This should be
	   good enough for now.

	4. Handle resolution is done synchronous, thereby defeating
	   the intended asynchronous API.  This should be fixed by
	   adding an asynchronous interface to hdllib.py.

"""

import sys
import hdllib
import nullAPI



# We are currently only concerned with URL type handles.
HANDLE_TYPES = [hdllib.HDL_TYPE_URL]


# HTML boilerplate for response on handle with multiple URLs
HTML_HEADER = """<HTML>

<HEAD>
<TITLE>Multiple URLs From Handle</TITLE>
</HEAD>

<BODY>

<H1>Multiple URLs</H1>

The handle you have selected resolves to multiple URLs.
Please select one from the following list:

<UL>
"""

HTML_TRAILER = """
</UL>

</BODY>

</HTML>
"""



global_hash_table = None
local_hash_tables = {}

def get_local_hash_table(hdl):
    key = hdllib.get_authority(hdl)
    if not local_hash_tables.has_key(key):
	#print "Fetching local hash table for", key
	local_hash_tables[key] = hdllib.fetch_local_hash_table(
	    key, global_hash_table)
    return local_hash_tables[key]


class hdl_access(nullAPI.null_access):

    _types = HANDLE_TYPES

    def __init__(self, hdl, method, params):
	nullAPI.null_access.__init__(self, hdl, method, params)
	# Can ignore methods and params... they should be 'GET' and {}
	# respectively
	self._hdl = hdl
	global global_hash_table
	if not global_hash_table:
	    try:
		#print "Fetching global hash table"
		global_hash_table = hdllib.fetch_global_hash_table()
	    except hdllib.Error, inst:
		raise IOError, inst, sys.exc_traceback

    def pollmeta(self):
	nullAPI.null_access.pollmeta(self)
	try:
	    replyflags, self._items = global_hash_table.get_data(
		self._hdl, self._types)
	except hdllib.Error, inst:
	    if inst.err == hdllib.HP_HANDLE_NOT_FOUND:
		# Retry using a local handle server
		try:
		    hashtable = get_local_hash_table(self._hdl)
		    replyflags, self._items = hashtable.get_data(
			self._hdl, self._types)
		except hdllib.Error, inst:
		    # (Same comment as below)
		    raise IOError, inst, sys.exc_traceback
		else:
		    return 'Ready', 1
	    # Catch all errors and raise an IOError.  The Grail
	    # protocol extension defines this as the only error we're
	    # allowed to raise.
	    # Because the hdllib.Error instance is passed, no
	    # information is lost.
	    raise IOError, inst, sys.exc_traceback
	else:
	    return 'Ready', 1

    def getmeta(self):
	nullAPI.null_access.getmeta(self)
	if len(self._items) == 1:
	    flags, uri = self._items[0]
	    return 302, 'Moved', {'location': uri}
	data = HTML_HEADER
	for flags, uri in self._items:
	    text = '<LI><A HREF="%s">%s</A>\n' % (uri, uri)
	    data = data + text
	data = data + HTML_TRAILER
	self._data = data
	self._pos = 0
	return 200, 'OK', {'content-type': 'text/html'}

    # polldata() is inherited from nullAPI

    def getdata(self, maxbytes):
	end = self._pos + maxbytes
	data = self._data[self._pos:end]
	if not data:
	    return nullAPI.null_access.getdata(self, maxbytes)
	self._pos = end
	return data


# Here are some handles to try out the multiple-URL reponse:
# hdl://nonreg.guido/python-home-page
# hdl://nonreg.guido/python-ftp-dir
