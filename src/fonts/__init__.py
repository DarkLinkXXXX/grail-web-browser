# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""PostScript font metrics package.

This package is used by the html2ps.py standalone script, and Grail's
PostScript printing dialog to gather the correct font metrics for
printing.

Exported functions:

font_from_name(psfontname)
	returns a PSFont derived object for metrics calculation

"""

import regsub

def font_from_name(psfontname):
    # PostScript fonts use dash delimiters, while Python module names
    # use underscores.
    modulename = 'PSFont_' + regsub.gsub('-', '_', psfontname)
    # no need to do any caching since the import mechanism does that
    # for us!
    module = __import__(modulename, globals(), locals())
    return module.font

# the general solution... gross!
for name in ['font_from_name', '__doc__']:
    setattr(__, name, vars()[name])
