"""Default style sheet for Grail's Viewer widget.

This class has no methods, only class variables.  It is not intended
to be instantiated; rather, you pass the class itself as the
stylesheet argument to the Viewer object.  It is useful to inherit
from it though, if you want to define a style sheet that is just a
little bit different.
"""

import string

STYLES_PREFS_PREFIX = 'styles-'

## NOTE: Link colors are taken from Netscape 1.1's X app defaults


class DefaultStylesheet:

    def __init__(self, prefs, sheet_nm):
	self.sheet_nm = sheet_nm
	self.prefs = prefs
	self.attrs = attrs = {}
	ck = sheet_nm + "-"
	l = len(ck)
	for [group, composite], val in (prefs.GetGroup('styles-common')
			       + prefs.GetGroup(self.group_name())):
	    fields = string.splitfields(composite, '-')
	    d = attrs
	    while fields:
		f = fields[0]
		del fields[0]
		if not fields:
		    # f is a terminal key:
		    d[f] = val
		elif d.has_key(f):
		    d = d[f]
		else:
		    d[f] = newd = {}
		    d = newd

    def __getattr__(self, composite):
	try:
	    attr = string.splitfields(composite, '.')[0]
	    return self.attrs[attr]
	except IndexError:
	    raise AttributeError, attr

    def group_name(self):
	return STYLES_PREFS_PREFIX + self.sheet_nm

def test():
    global grail_root
    grail_root = '.'
    import sys
    sys.path = ['./utils', './ancillary'] + sys.path
    import GrailPrefs
    prefs = GrailPrefs.AllPreferences()
    sheet = DefaultStylesheet(prefs, 'basic')
    print sheet.default
    print sheet.styles['h5_b']['font']

if __name__ == "__main__":
    test()
