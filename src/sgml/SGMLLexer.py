# $Id: SGMLLexer.py,v 1.1 1996/03/14 22:57:17 fdrake Exp $
"""A lexer, parser for SGML, using the derived class as static DTD.

This only supports those SGML features used by HTML.
See W3C tech report: 'A lexical analyzer for HTML and Basic SGML'
http://www.w3.org/pub/WWW/MarkUp/SGML/sgml-lex/sgml-lex.html
"""
# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


try:
    import sgmllex # compiled flex scanner
except ImportError:
    import regex
    _sgmllex = 0
else:
    _sgmllex = 1

import string


SGMLError = 'SGMLLexer.SGMLError'


# SGML lexer base class -- find tags and call handler functions.
# Usage: p = SGMLLexer(); p.feed(data); ...; p.close().
# The data
# between tags is passed to the parser by calling self.handle_data()
# with some data as argument (the data may be split up in arbutrary
# chunks).  Entity references are passed by calling
# self.handle_entityref() with the entity reference as argument.


class SGMLLexerBase:
    #  This is a "dummy" base class which provides documentation on the
    #  lexer API; this can be used by tools which can extract missing
    #  method documentation from base classes.

    def feed(self, input_data):
	"""Feed some data to the parser.

	Call this as often as you want, with as little or as much text
	as you want (may include '\n').  Pass empty string to indicate
	EOF.
	"""
	pass

    def close(self):
	"""Terminate the input stream.

	If any data remains unparsed or any events have not been
	dispatched, they must be forced to do so by this method before
	returning.
	"""
	pass

    #  The rest of the methods of this class are intended to be overridden
    #  by parser subclasses interested in different events on the input
    #  stream.  They are called by the implementation of the lexer object.

    def lex_data(self, data_string):
	"""Process data characters.
	"""
	pass

    def lex_starttag(self, tagname, attributes):
	"""Process a start tag and attributes.

	The `tagname' is the name of the tag encountered, and `attributes'
	is a dictionary of the attribute/value pairs found in the document
	source.  The tagname and attribute names are normalized to lower
	case; all attribute values are strings.  Attribute values coded as
	string literals using either LIT or LITA quoting will have the
	surrounding quotation marks removed.  Attributes with no value
	specified in the document source will have a value of None in the
	dictionary passed to this method.
	"""
	pass

    def lex_endtag(self, tagname):
	"""Process an end tag.
	"""
	pass

    def lex_charref(self, ordinal):
	"""Process a numeric character reference.
	"""
	pass

    def lex_namedcharref(self, refname):
	"""Process a named character reference.
	"""
	pass

    def lex_entityref(self, refname):
	"""Process a general entity reference.
	"""
	pass

    def lex_pi(self, pi_data):
	"""Process a processing instruction.
	"""
	pass

    def lex_comment(self, comment_string):
	"""Process a comment string.

	If a markup declaration consists entirely of comments, each comment
	is passed to this method in sequence.  The parser has no way of
	knowing whether multiple comments received in sequence are part of
	a single markup declaration or originated in multiple declarations.
	Empty comments ('<!>') are ignored.  Comments embedded in other
	markup declarations are not handled via this method.
	"""
	pass

    def lex_declaration(self, declaration_text):
	"""Process a markup declaration other than a comment.

	`declaration_info' will be a string containing the text of the
	markup declaration, possibly normalized for whitespace and case.
	"""
	pass


class SGMLLexer(SGMLLexerBase):
    if _sgmllex:
	def __init__(self):
	    self._l = sgmllex.scanner(self.lex_data,
				      self._lex_got_stag,
				      self._lex_got_etag,
				      self.lex_charref,
				      self._lex_got_namedcharref,
				      self._lex_got_geref,
				      self._lex_aux,
				      self._lex_err)
	    self._l.normalize(1)

	# Interface -- f
	def feed(self, data):
	    self._l.scan(data)

	#def line(self):
	#    """Retrieves the current line number of the lexer object.
	#    """
	#    return self._l.line()

	def close(self):
	    """Flush any remaining data in the lexer's internal buffer.
	    """
	    self.feed('')

	def _lex_got_geref(self, entname):
	    self.lex_entityref(entname[1:])

	def _lex_got_namedcharref(self, name):
	    self.lex_namedcharref(name[2:])

	def _lex_got_etag(self, tagname):
	    self.lex_endtag(tagname[2:])

	def _lex_got_stag(self, name, attributes):
	    self.lex_starttag(name[1:], attributes)

	def _lex_aux(self, types, strings):
	    if types[0] is sgmllex.comment:
		# strip of leading/trailing --
		map(lambda s,f=self.lex_comment: f(s[2:-2]), strings)

	    elif types[0] is sgmllex.processingInstruction:
		# strip <? and >
		self.lex_pi(strings[0][2:-1])
	    else:
		#XXX markup declarations, etc.
		self.lex_declaration(string.joinfields(strings, ' '))

	def _lex_err(self, types, strings):
	    #  raise SGMLError?
	    pass

    else:				# sgmllex not available

	def __init__(self):
	    pass


if not _sgmllex:
    # Regular expressions used for parsing:
    interesting = regex.compile('[&<]')
    incomplete = regex.compile('&\([a-zA-Z][a-zA-Z0-9]*\|#[0-9]*\)?\|'
			       '<\([a-zA-Z][^<>]*\|'
			       '/\([a-zA-Z][^<>]*\)?\|'
			       '![^<>]*\)?')

    entityref = regex.compile('&\([a-zA-Z][a-zA-Z0-9]*\)[^a-zA-Z0-9]')
    charref = regex.compile('&#\([0-9]+\)[^0-9]')

    starttagopen = regex.compile('<[>a-zA-Z]')
    shorttagopen = regex.compile('<[a-zA-Z][a-zA-Z0-9]*/')
    shorttag = regex.compile('<\([a-zA-Z][a-zA-Z0-9]*\)/\([^/]*\)/')
    endtagopen = regex.compile('</[<>a-zA-Z]')
    endbracket = regex.compile('[<>]')
    special = regex.compile('<![^<>]*>')
    commentopen = regex.compile('<!--')
    commentclose = regex.compile('--[ \t\n]*>')
    tagfind = regex.compile('[a-zA-Z][a-zA-Z0-9]*')
    attrfind = regex.compile( \
	'[ \t\n]+\([a-zA-Z_][a-zA-Z_0-9]*\)'
	'\([ \t\n]*=[ \t\n]*'
	'\(\'[^\']*\'\|"[^"]*"\|[-a-zA-Z0-9./:+*%?!()_#=]*\)\)?')


# SGML parser class -- find tags and call handler functions.
# Usage: p = SGMLParser(); p.feed(data); ...; p.close().
# The dtd is defined by deriving a class which defines methods
# with special names to handle tags: start_foo and end_foo to handle
# <foo> and </foo>, respectively, or do_foo to handle <foo> by itself.
# (Tags are converted to lower case for this purpose.)
# XXX what about periods, hyphens in tag names?

class SGMLParser(SGMLLexer):

	# Interface -- initialize and reset this instance
	def __init__(self, verbose = 0):
	    self.verbose = verbose
	    SGMLLexer.__init__(self)
	    self.reset()

	# Interface -- reset this instance.  Loses all unprocessed data
	def reset(self):
	    self.stack = []
	    self.cdata = 0

	# For derived classes only -- enter literal mode (CDATA)
	def setliteral(self, *args):
	    self.cdata = 1 #@@ finish implementing this...

	def startTag(self, tag, attrs):
	    try:
		method = getattr(self, 'start_' + tag)
	    except AttributeError:
		try:
		    method = getattr(self, 'do_' + tag)
		except AttributeError:
		    self.unknown_starttag(tag, attrs)
		    return
		method(attrs)
	    else:
		self.stack.append(tag)
		method(attrs)

	def lex_endtag(self, tag):
	    try:
		method = getattr(self, 'end_' + tag)
	    except AttributeError:
		self.unknown_endtag(tag)
		return
	    if self.stack and self.stack[-1] == tag:
		del self.stack[-1]
	    else:
		self.report_unbalanced(tag)
		# Now repair it
		found = None
		for i in range(len(self.stack)):
		    if self.stack[i] == tag: found = i
		if found <> None:
		    del self.stack[found:]
	    method()

	# Example -- report an unbalanced </...> tag.
	def report_unbalanced(self, tag):
	    if self.verbose:
		print '*** Unbalanced </' + tag + '>'
		print '*** Stack:', self.stack

	# Definition of entities -- derived classes may override
	entitydefs = \
		   {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"'}

	# Example -- handle entity reference, no need to override
	def handle_entityref(self, name):
	    table = self.entitydefs
	    if table.has_key(name):
		self.handle_data(table[name])
	    else:
		self.unknown_entityref(name)

	# Example -- handle data, should be overridden
	def handle_data(self, data): pass

	# Example -- handle comment, could be overridden
	def handle_comment(self, data): pass

	# Example -- handle processing instruction, could be overridden
	def handle_pi(self, data): pass

	# To be overridden -- handlers for unknown objects
	def unknown_starttag(self, tag, attrs): pass
	def unknown_endtag(self, tag): pass
	def unknown_entityref(self, ref): pass
	def unknown_namedcharref(self, ref): pass
	def report_unbalanced(self, tag): pass



def test():
    import sys
    f = sys.stdin
    x = TestSGML()
    while 1:
	line = f.readline()
	if not line:
	    x.close()
	    break
	x.feed(line)


if __name__ == '__main__':
    test()
