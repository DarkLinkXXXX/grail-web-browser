"""Support for client-side image maps."""

import string

class Shape:
    """shaped regions for client-side image maps."""

    def __init__(self, kind, coords, url):
	self.kind = kind
	self.coords = coords
	self.url = url

    def pointin(self, x, y):
	"""predicate: Are x,y coordinates within region?"""
	isin = 0
	if self.kind == 'rect':
	    if self.coords[0][0] <= x <= self.coords[1][0] and self.coords[0][1] <= y <= self.coords[1][1]:
		isin = 1

	elif self.kind == 'circle':
	    # is the distance from the point to the center of the
	    # circle less than the radius? 
 	    distance_squared = pow((self.coords[0][0] - x), 2) + pow((self.coords[0][1] - y), 2)  
	    if distance_squared <= pow(self.coords[1], 2):
		isin = 1

	elif self.kind == 'poly':
	    isin = poly_pointin(self, x, y)

	elif self.kind == 'default':
	    isin = 1

	return isin

    def poly_pointin(self, x, y):
	return 0

class MapInfo:
    """Holds shapes during parsing.

    The shapes are copied into a MapThunk object when the map is used.
    """

    def __init__(self, parser, name):
	self.parser = parser
	self.name = name
	self.shapes = []

    def add_shape(self, kind, coords, url):
	self.shapes.append(Shape(kind, coords, url))


class MapThunk:
    """Map interface for an ImageWindow, will wait for MAP to be parsed.

    The <MAP> tag may not have been parsed by the time the user clicks
    on the image, particularly if the USEMAP attribute specifies a MAP
    in a different page. Initially, the map has no shapes and it waits
    until the method url() is called, which calls force to load the
    shapes from the parser. If force() fails, then url returns None
    and the next call to url() will also invoke force().

    get_shape() memoizes the shape object at a particular (x,y)
    coordinate because the lookup could be slow when there are many
    shapes. not sure if this is necessary/desirable.
    """

    def __init__(self, parser, name):
	"""Link MapThunk to the parser containing the map."""

	self.parser = parser
	self.name = name
	self.shapes = []
	self.waiting = 1
	self.memo = {}

    def force(self):
	"""Try to load shapes from the parser."""

	try:
	    map = self.parser.image_maps[self.name]
	    self.shapes = map.shapes
	    self.waiting = 0
	except KeyError:
	    pass
    
    def url(self, x, y):
	"""Get url associated with shape at (x,y)."""

	# first check to see if the map has been parsed
	if self.waiting == 1:
	    self.force()
	    if self.waiting == 1:
		return None

	# get the shape and return url
	shape = self.get_shape(x, y)
	if shape:
	    return shape.url
	else:
	    return None

    def get_shape(self, x, y):
	"""Get shape at coords (x,y)."""
	try:
	    # memoize good for lots of shapes
	    return self.memo[(x,y)]
	except KeyError:
	    # does this iterate through in order?
	    # it should so that overlapping shapes are handled properly
	    for shape in self.shapes:
		if shape.pointin(x, y) == 1:
		    self.memo[(x,y)] = shape
		    return shape
	    return None

