"""Default style sheet for Grail's Viewer widget.

Instantiate DefaultStylesheet with the name of the sheet.  It gets the
command and sheet-specific values as, effectively, class attributes with
dictionary values suitable for feeding to the text widget for tag
configuration."""

import string

UndefinedStyle = 'UndefinedStyle'

LastOkStyle = None

STYLES_PREFS_PREFIX = 'styles-'

## NOTE: Link colors are taken from Netscape 1.1's X app defaults


class DefaultStylesheet:

    registered_style_validator = 0

    def __init__(self, prefs, sheet_name):
	global LastOkStyle
	self.sheet_name = sheet_name
	self.prefs = prefs
	self.attrs = attrs = {}
	name = self.group_name(sheet_name)
	group_prefs = prefs.GetGroup(name)
	if not group_prefs:
	    self.reset_group_name(name)
	    raise UndefinedStyle
	for (group, composite), val in (prefs.GetGroup('styles-common')
					+ group_prefs):
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
	LastOkStyle = name

    def __getattr__(self, composite):
	try:
	    attr = string.splitfields(composite, '.')[0]
	    return self.attrs[attr]
	except IndexError:
	    raise AttributeError, attr

    def reset_group_name(self, name):
	"""When we hit bad style name, revert to last good or factory setting.
	"""
	global LastOkStyle
	if LastOkStyle:
	    reverting_to = LastOkStyle
	else:
	    reverting_to = self.prefs.Get('styles', 'group', use_default=1)

	print ('Bad style group %s, reverting pref to %s'
	       % (`name`, `reverting_to`))
	self.prefs.Set('styles', 'group', reverting_to)

    def group_name(self, sheet_name):
	return STYLES_PREFS_PREFIX + str(sheet_name)

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
