"""Default style sheet for Grail's Viewer widget.

Instantiate DefaultStylesheet with the name of the sheet.  It gets the
command and sheet-specific values as, effectively, class attributes with
dictionary values suitable for feeding to the text widget for tag
configuration."""

import string

UndefinedStyle = 'UndefinedStyle'

## NOTE: Link colors are taken from Netscape 1.1's X app defaults


class DefaultStylesheet:

    registered_style_validator = 0

    def __init__(self, prefs, sizename, family):
	self.sizename = sizename
	self.family = family
	self.prefs = prefs
	self.attrs = attrs = {}

	self.size, fparms_dict = self.get_sizes()
	fparms_dict['family'] = self.get_family()
	fparms_dict['italic'] = self.get_italic()

	self.dictify_group(prefs.GetGroup('styles-common'))

	# Map the selected font and size onto the fonts group:
	fonts = prefs.GetGroup('styles-fonts')
	massaged = []
	for ((g, c), v) in fonts:
	    massaged.append((g, c), v % fparms_dict)
	self.dictify_group(massaged)

    def __getattr__(self, composite):
	"""Make the self.attr dict keys look like class attributes."""
	try:
	    attr = string.splitfields(composite, '.')[0]
	    return self.attrs[attr]
	except IndexError:
	    raise AttributeError, attr

    def get_sizes(self):
	"""Get the size name and a dictionary of size name/values.

	Detects unregistered sizes and uses registered default-size."""
	allsizes = string.split(self.prefs.Get('styles', 'all-sizes'))
	sname = self.sizename
	if sname not in allsizes:
	    sname = self.prefs.Get('styles', 'default-size')
	    if sname not in allsizes:
		raise UndefinedStyle, ("Bad preferences file,"
				       + " can't get valid size.")
	sdict = {}
	slist = string.split(self.prefs.Get('styles', sname + '-sizes'))
	atoi = string.atoi
	for k in string.split(self.prefs.Get('styles', 'size-names')):
	    sdict[k] = atoi(slist[0])
	    del slist[0]
	return sname, sdict

    def get_italic(self):
	"""Get the character for oblique fonts in the family."""
	return self.prefs.Get('styles', self.family + '-italic')

    def get_family(self):
	"""Get the family name and a dictionary of size name/values.

	Detects unregistered families and uses registered default-family."""
	allfams = string.split(self.prefs.Get('styles', 'all-families'))
	tname = self.family
	if tname not in allfams:
	    tname = self.prefs.Get('styles', 'default-family')
	    if tname not in allfams:
		raise UndefinedStyle, ("Bad preferences file,"
				       + " can't get valid family.")
	return tname

    def dictify_group(self, glist, attr=None):
	"""Incorporate entries in preferences GetGroup list to self.attrs."""
	attrs = self.attrs
	for (group, composite), val in glist:
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


def test():
    global grail_root
    grail_root = '.'
    import sys
    sys.path = ['./utils', './ancillary'] + sys.path
    import GrailPrefs
    prefs = GrailPrefs.AllPreferences()
    sheet = DefaultStylesheet(prefs, 'basic', 'helvetica')
    print sheet.styles['h5_b']['font']

if __name__ == "__main__":
    test()
