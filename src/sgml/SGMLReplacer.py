"""Simple parser that handles only what's allowed in attribute values.
"""
__version__ = '$Revision: 1.3 $'
#  $Source: /home/john/Code/grail/src/sgml/SGMLReplacer.py,v $


import string
from SGMLLexer import *



class SGMLReplacer(SGMLLexer):
    """Simple lexer for interpreting entity references in attribute values.

    Given an attribute from a start tag, passing it through a descendent
    of this class allows replacement of general entity references found in
    the string:

	replacer = SGMLReplacer(entity_dict)
	replacer.feed(attribute_value)
	attribute_value = replacer.getvalue()
    """
    entitydefs = {}

    def __init__(self, entities = None, whitespace = string.whitespace):
	SGMLLexer.__init__(self)
	self._data = ''
	self._white = whitespace
	if entities:
	    self.entitydefs = entities

    def getvalue(self):
	self.close()
	return _normalize_whitespace(self._data, self._white)

    def lex_starttag(self, name, attributes):
	raise SGMLError, 'tags in attribute values are illegal'

    def lex_endtag(self, name):
	raise SGMLError, 'tags in attribute values are illegal'

    def lex_charref(self, ordinal):
	if 0 < ordinal < 256:
	    self._data = self._data + chr(ordinal)
	else:
	    self.unknown_charref(ordinal)

    def lex_data(self, str):
	self._data = self._data + str

    def lex_entityref(self, name):
	if self.entitydefs.has_key(name):
	    self._data = self._data + self.entitydefs[name]
	else:
	    self.unknown_entityref(name)

    named_characters = {'re' : '\r',
			'rs' : '\n',
			'space' : ' '}

    def lex_namedcharref(self, name):
	if self.named_characters.has_key(name):
	    self._data = self._data + self.named_characters[name]
	else:
	    self.unknown_namedcharref(name)

    def lex_pi(self, pi):
	# Should never be called, but let's make sure we're ok:
	self._data = '%s%s%s%s' % (self._data, PIO, pi, PIC)

    def unknown_entityref(self, name, terminator):
	self._data = '%s%s%s%s' % (self._data, ERO, name, terminator)

    def unknown_namedcharref(self, name, terminator):
	self._data = '%s%s%s%s' % (self._data, CRO, name, terminator)

    def unknown_charref(self, ordinal, terminator):
	self._data = '%s%s%s%s' % (self._data, CRO, `ordinal`, terminator)


def replace(data, entities = None):
    """Perform general entity replacement on a string.
    """
    if '&' in data:
	replacer = SGMLReplacer(entities)
	replacer.feed(data)
	return replacer.getvalue()
    else:
	return _normalize_whitespace(data)


def _normalize_whitespace(data, whitespace = string.whitespace):
    """Replaces sequences of whitespace with a single space.
    """
    if data:
	if data[0] in whitespace:
	    data = data[1:]
	    s = ' '
	else:
	    s = ''
	for c in data:
	    if c in whitespace:
		if s[-1] != ' ':
		    s = s + ' '
	    else:
		s = s + c
	return s
    return ''


#
#  end of file
