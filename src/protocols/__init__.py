# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

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
