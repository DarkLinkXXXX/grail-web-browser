"""CNRI handle protocol extension.

This module glues the backend CNRI handle client resolution module in
hdllib.py to the Grail 0.2 URI protocol API.  Currently we are only
interested in URL type handles, so we can get away semantically with
returning an HTTP-style relocation error to the browser for the
resolved handle.

Problems as of 25-Oct-1995:

	1. hdllib.py currently only supports the older handle
	   protocol.  Specifically, it doesn't support dynamic
	   downloading of the hash table, and consequently it doesn't
	   support local handle servers.  This isn't a big deal
	   currently because no local handle servers have been
	   deployed, and the global system is backward compatible with
	   the old protocol.

	2. I don't think it handles continuation packets correctly.
	   This isn't a big deal since in this context, we're only
	   concerned with URL type values, which are smaller than the
	   packet size.

	3. Issuing a 302 relocate isn't the proper thing to do in the
	   long term, because it forces the user back into URL space.
	   So, for example, the user will naturally keep the resolved
	   URL on her bookmarks, instead of the original handle.
	   However, for backward compatibility with relative links, we
	   need to define relative-handle semantics.  We're working
	   with the CNRI handle group to define this and we'll be
	   experimenting with solutions in the future.  This should be
	   good enough for now.
"""

import hdllib
import nullAPI



# We are currently only concerned with URL type handles.
HANDLE_TYPES = [hdllib.HDL_TYPE_URL]



class HandleResolutionChooser:
    """Abstract class implementing selection of a single handle
    resolution from a list of resolutions.  A handle can actually
    resolve to multiple URLs and we need a way to select between them.
    The default (this class) is to simply choose one randomly out of
    the list.  Other selection mechanisms can include generating an
    HTML page containing all the links, or popping up a GUI selection
    list dialog and letting the user choose.

    Methods to Override:

       choose(handle_resolution_list)  -- returns one item from the list
    """
    def choose(self, handle_resolution_list):
	import rand
	return rand.choice(handle_resolution_list)
    


class hdl_access(nullAPI.null_access):
    def __init__(self, uri, method, params):
	nullAPI.null_access.__init__(self, uri, method, params)
	# can ignore methods and params... they should be 'GET' and {}
	# respectively
	self._uri = uri
	self._types = HANDLE_TYPES
	self._chooser = HandleResolutionChooser()

    def set_chooser(self, chooser):
	oldchooser = self._chooser
	self._chooser = chooser
	return oldchooser

    def _error(self):
	import sys
	import TbDialog
	from __main__ import app
	TbDialog.TracebackDialog(app.root, sys.exc_type,
				 sys.exc_value, sys.exc_traceback)

    def pollmeta(self):
	nullAPI.null_access.pollmeta(self)
	try:
	    hashtable = hdllib.HashTable()
	    replyflags, self._items = \
			hashtable.get_data(self._uri, self._types)
	except:
	    # catch all errors and raise an IOError.  The Grail
	    # protocol extension defines this as the only error we're
	    # allowed to raise.
#	    self._error()
	    raise IOError
	return 'Ready', 1

    def getmeta(self):
	nullAPI.null_access.getmeta(self)
	try:
	    flags, uri = self._chooser.choose(self._items)
	except:
	    self._error()
	    raise IOError
	# return `document has temporarily moved'
	return 302, 'Moved', {'location': uri}
