"""Parses <AREA> tag for client-side imagemaps."""

from map import MapInfo
import string

def do_area(parser, attrs):
    """Handle the <AREA> tag."""

    # use try because we may not have seen a map yet, which means
    # the <MAP> instance variables haven't been added to the parser
    try:
	if parser.current_map:
	    coords = []
	    shape = 'rect'
	    url = ''
	    alt = ''

	    for name, val in attrs:
		if name == 'shape':
		    shape = val
		if name == 'coords':
		    coords = val
		if name == 'alt':
		    alt = val
		if name == 'href':
		    url = val
		if name == 'nohref':  # not sure what the point is
		    url = None

	    parser.current_map.add_shape(shape, parse_coords(shape, coords), url)
    except AttributeError:
	pass # ignore, because we're not in a map

def parse_coords(shape, text):
    """Parses coordinate string into list of numbers.

    Coordinates are stored differently depending on the shape of the object.
    """
    coords = []
    terms = []

    string_terms = string.splitfields(text, ',')
    for i in range(len(string_terms)):
	terms.append(string.atoi(string_terms[i]))
    
    if shape == 'poly':
	# list of (x,y) tuples
	while len(terms) > 0:
	    coords.append((terms[0], terms[1]))
	    del terms[0:1]
    elif shape == 'rect':
	# (x,y) tuples for upper left, lower right
	coords.append((terms[0], terms[1]))
	coords.append((terms[2], terms[3]))
    elif shape == 'circle':
	# (x,y) tuple for center, followed by int for radius
	coords.append((terms[0], terms[1]))
	coords.append(terms[2])
    return coords

