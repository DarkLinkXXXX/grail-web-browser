"""Protocol schemes package.

This package supports a high level interface to importation of support
for URL protocol schemes.

Exported functions:

protocol_access(url, mode, params, data=None)
	returns the protocol scheme object for the scheme specified in
	the URL.

"""

import ProtocolAPI

for name in ['protocol_access', '__doc__']:
    setattr(__, name, getattr(ProtocolAPI, name))
