"""Handler for inline images expressed using <OBJECT>.
"""
__version__ = "$Revision: 1.1 $"
# $Source: /home/john/Code/grail/src/obj_viewer/Attic/image.py,v $

import HTMLParser
import string
import Tkinter

from grailutil import *


def embed_image(parser, attrs):
    src = extract_keyword('data', attrs)
    if src:
	src = parser.context.get_baseurl(src)
    if not src:
	return None
    if not parser.context.app.prefs.GetBoolean('browser', 'load-images'):
	return None
    datatype, typeopts = extract_keyword('type', attrs, conv=conv_mimetype)
    if not datatype:
	datatype, typeopts = conv_mimetype(parser.context.app.guess_type(src))
	if not datatype:
	    return None
    shapes = attrs.has_key('shapes')
    border = extract_keyword('border', attrs, shapes and 2 or 0,
			     conv=string.atoi)
    width = extract_keyword('width', attrs, 0, conv=string.atoi)
    height = extract_keyword('height', attrs, 0, conv=string.atoi)
    hspace = extract_keyword('hspace', attrs, 0, conv=string.atoi)
    vspace = extract_keyword('vspace', attrs, 0, conv=string.atoi)
    return ImageObject(parser, src, shapes=shapes, border=border, width=width,
		       height=height, hspace=hspace, vspace=vspace)


class ImageObject(HTMLParser.Embedding):
    __map = None

    def __init__(self, parser, src, shapes=0, border=0, width=0,
		 height=0, hspace=0, vspace=0):
	if shapes:
	    self.__map, thunk = self.__make_map(parser.context)
	else:
	    thunk = None
	print "Creating ImageObject handler", self, "data=" + src
        parser.handle_image(src, '', thunk, 0,
			    Tkinter.BASELINE, width, height, border,
			    parser.reload1, hspace=hspace, vspace=vspace)

    def __make_map(self, context):
	global __map_count
	try:
	    __map_count = __map_count + 1
	except NameError:
	    __map_count = 0
	name = '<OBJECT-MAP-%d>' % __map_count
	import ImageMap
	map = ImageMap.MapInfo(name)
	context.image_maps[name] = map
	return map, ImageMap.MapThunk(context, name)

    def anchor(self, attrs):
	if not self.__map:
	    return
	href = extract_keyword('href', attrs)
	if not href:
	    return
	target = extract_keyword('target', attrs, "", conv=conv_normstring)
	shape = extract_keyword('shape', attrs, conv=conv_nomstring)
	coords = extract_keyword('coords', attrs, conv=conv_normstring)
	if shape and (coords or shape == 'default'):
	    self.__map.add_shape(shape, coords, href, target)

#
#  end of file
