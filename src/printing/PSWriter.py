"""Wrapper for the PSStream to support the standard AbstractWriter interface.
"""
__version__ = '$Revision: 1.1 $'
#  $Source: /home/john/Code/grail/src/printing/PSWriter.py,v $

import formatter
import string


class PSWriter(formatter.AbstractWriter):
    """Class PSWriter supports the backend interface expected by
    Grail, actually the HTMLParser class.  It does this by deriving
    from AbstractWriter and overriding methods to interface with the
    PSStream class, which performs the real PostScript work.

    Exported methods:

      __init__(OUTPUT_FILE_OBJECT, optional:TITLE)
      close()
      new_font(FONT_TUPLE)
      new_margin(MARGIN_TAG(ignored) LEVEL)
      new_spacing(SPACING)
      new_styles(STYLE_TUPLE)
      send_paragraph(NUMBER_OF_BLANKLINES)
      send_line_break()
      send_hor_rule()
      send_label_data(LABEL_TAG)
      send_flowing_data(TEXT)
      send_literal_data(TEXT)

    Exported ivars:
    """
    __detab_pos = 0

    def __init__(self, ofile, title='', url='',
		 varifamily='Times', fixedfamily='Courier', paper=None,
		 fontsize=None, leading=None):
	if not title:
	    title = url
	import PSFont
	import PSStream
	font = PSFont.PSFont(varifamily=varifamily,
			     fixedfamily=fixedfamily,
			     size=fontsize)
	self.ps = PSStream.PSStream(font, ofile, title, url, paper=paper)
	if leading:
	    self.ps.set_leading(leading)
	self.ps.start()
## 	self.new_alignment = self.ps.push_alignment
## 	self.new_font = self.ps.push_font_change

    def close(self):
##	utils.debug('close')
	self.ps.push_end()

    def new_alignment(self, align):
##	utils.debug('new_alignment: %s' % `align`)
	self.ps.push_alignment(align)

    def new_font(self, font):
##	utils.debug('new_font: %s' % `font`)
	self.ps.push_font_change(font)

    def new_margin(self, margin, level):
##	utils.debug('new_margin: margin=%s, level=%s' % (margin, level))
	self.ps.push_margin(level)
	self.__detab_pos = 0

    def new_spacing(self, spacing):
	raise RuntimeError, 'not yet implemented'

	# semantics of STYLES is a tuple of single char strings.
	# Right now the only styles we support are lower case 'underline' for
	# underline and a 'blockquote' for each right-hand indentation.
    def new_styles(self, styles):
##	utils.debug('new_styles: %s' % styles)
	self.ps.push_underline('underline' in styles)
	self.ps.push_rightmargin(map(None, styles).count('blockquote'))

    def send_paragraph(self, blankline):
##	utils.debug('send_paragraph: %s' % blankline)
	self.ps.push_paragraph(blankline)
	self.__detab_pos = 0

    def send_line_break(self):
##	utils.debug('send_line_break')
	self.ps.push_hard_newline()
	self.__detab_pos = 0

    def send_hor_rule(self, abswidth=None, percentwidth=None,
		      height=None, align=None):
##	utils.debug('send_hor_rule')
	self.ps.push_horiz_rule(abswidth, percentwidth, height, align)
	self.__detab_pos = 0

    def send_label_data(self, data):
##	utils.debug('send_label_data: %s' % data)
	self.ps.push_label(data)
	self.__detab_pos = 0

    def send_flowing_data(self, data):
##	utils.debug('send_flowing_data: %s' % data)
	self.ps.push_literal(0)
	self.ps.push_string_flowing(data)
	self.__detab_pos = 0

    def send_literal_data(self, data):
##	utils.debug('send_literal_data: %s' % data)
	self.ps.push_literal(1)
	self.ps.push_string(self.__detab_data(data))

    def send_eps_data(self, image, align):
##	utils.debug('send_eps_data: <epsdata>, ' + `bbox`)
	self.ps.push_eps(image, align)
	self.__detab_pos = 0

    def __detab_data(self, data):
	pos = self.__detab_pos
	s = []
	append = s.append
	for c in data:
	    if c == '\n':
		append('\n')
		pos = 0
	    elif c == '\t':
		append(' ' * (8 - (pos % 8)))
		pos = 0
	    else:
		append(c)
		pos = pos + 1
	self.__detab_pos = pos
	return string.joinfields(s, '')

#
#  end of file