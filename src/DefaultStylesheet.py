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

    def __init__(self, prefs, sizename, typename):
	self.sizename = sizename
	self.typename = typename
	self.prefs = prefs
	self.attrs = attrs = {}

	self.size, fparms_dict = self.get_sizes()
	fparms_dict['type'] = self.get_type()
	fparms_dict['italic'] = self.get_italic()

	self.dictify_group(prefs.GetGroup('styles-common'))

	# Map the selected font and size onto the fonts group:
	fonts = prefs.GetGroup('styles-fonts')
	massaged = []
	for ((g, c), v) in fonts:
	    massaged.append((g, c), v % fparms_dict)
	    #((g, c), v) = it
	    #if c[-5:] == "-font":
	    #	if index(c, "%s") != -1
	    #	sz = atoi(sizes_dict[nm])
	    #	if nm[:3] == "_tt":
	    #	    massaged.append((g, c), v % sz)
	    #	else:
	    #	    massaged.append((g, c), v % (typename, sz))
	    #else:
	    #	massaged.append(it)
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
	"""Get the character for oblique fonts in the type."""
	return self.prefs.Get('styles', self.typename + '-italic')

    def get_type(self):
	"""Get the type name and a dictionary of size name/values.

	Detects unregistered types and uses registered default-type."""
	alltypes = string.split(self.prefs.Get('styles', 'all-types'))
	tname = self.typename
	if tname not in alltypes:
	    tname = self.prefs.Get('styles', 'default-type')
	    if tname not in alltypes:
		raise UndefinedStyle, ("Bad preferences file,"
				       + " can't get valid type.")
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
