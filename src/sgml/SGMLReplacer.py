"""Simple parser that handles only what's allowed in attribute values.
"""
__version__ = '$Revision: 1.1 $'
#  $Source: /home/john/Code/grail/src/sgml/SGMLReplacer.py,v $


import SGMLLexer
import string


class SGMLReplacer(SGMLLexer.SGMLLexer):
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
	self.feed('')
	return _normalize_whitespace(self._data, self._white)

    def got_stag(self, name, attributes):
	raise SGMLError, 'tags in attribute values are illegal'

    got_etag = got_stag

    def handle_data(self, str):
	self._data = self._data + str

    def handle_entityref(self, name):
	if self.entitydefs.has_key(name):
	    self._data = self._data + self.entitydefs[name]
	else:
	    self.unknown_entityref(name)

    def aux(self, *notused):
	raise SGMLError, 'markup declarations in attribute values are illegal'

    def unknown_entityref(self, *notused):
	pass

    def unknown_namedcharref(self, *notused):
	pass

    def unknown_charref(self, *notused):
	pass


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
