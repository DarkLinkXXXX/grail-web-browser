# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""Font metrics base class.

This module provides the interface for accurate font metrics generated
from the Adobe AFM files.  The generation script is a simple C program
that uses Adobe's AFM conversion library parseAFM.c, available from
ftp.adobe.com.  You can get Adobe's AFM files from the same ftp site.
See the comments at the tail of this file for the little C wrapper I
wrote to generate the PSFont_*.py files.

This module has its origins in code contributed by Fredrik Lundh
<Fredrik_Lundh@ivab.se> who contributed the framework for the Grail
0.2 release.  Thanks Fredrik!

"""

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
