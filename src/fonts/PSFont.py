"""Base class for font metrics generated from the Adobe AFM files using
their parseAFM.c library."""

import string
import array

class PSFont:
    def __init__(self, fontname, fullname, metrics):
	self._fontname = fontname
	self._fullname = fullname
	self._metrics = metrics

    def fontname(self): return self._fontname
    def fullname(self): return self._fullname

    def text_width(self, fontsize, str):
	"""Quickly calculate the width in points of the given string
	in the current font, at the given font size.
	"""
	width = 0
	metrics = self._metrics
	for ci in map(ord, str):
	    width = width + metrics[ci]
	return width * fontsize / 1000


if __name__ == '__main__':
    import PSFont_Times_Roman
    font = PSFont_Times_Roman.font

    print 'Font Name:', font.fontname()
    print 'Full Name:', font.fullname()
    print 'Width of "Hello World" in 12.0:', \
	  font.text_width(12.0, 'Hello World')
