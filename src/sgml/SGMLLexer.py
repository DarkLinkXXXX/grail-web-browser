# $Id: SGMLLexer.py,v 1.2 1996/03/15 19:34:37 fdrake Exp $
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

    def normalize(self, norm):
	"""Control normalization of name tokens.

	If `norm' is true, names tokens will be converted to lower
	case before being based to the lex_*() interfaces described
	below.  Otherwise, names will be reported in the case in which
	they are found in the input stream.  Tokens which are affected
	include tag names, attribute names, and named character
	references.  Note that general entity references are not
	affected.

	A boolean indicating the previous value is returned.
	"""
	pass

    def reset(self):
	"""Attempt to reset the lexical analyzer.
	"""
	pass

    def restrict(self, strict):
	"""Control recognition of particular constructs.
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
	    self.reset()

	def feed(self, data):
	    self._l.scan(data)

	def normalize(self, norm):
	    return self._l.normalize(norm)

	def reset(self):
	    self._l = sgmllex.scanner(self.lex_data,
				      self._lex_got_starttag,
				      self._lex_got_endtag,
				      self.lex_charref,
				      self._lex_got_namedcharref,
				      self._lex_got_geref,
				      self._lex_aux,
				      self._lex_err)

	def restrict(self, strict):
	    return self._l.restrict(strict)

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

	def _lex_got_endtag(self, tagname):
	    self.lex_endtag(tagname[2:])

	def _lex_got_startttag(self, name, attributes):
	    self.lex_starttag(name[1:], attributes)

	def _lex_aux(self, types, strings):
	    if types[0] is sgmllex.comment:
		# strip of leading/trailing --
		map(lambda s,f=self.lex_comment: f(s[2:-2]), strings[1:-1])

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
	    self.rawdata = ''
	    self.stack = []
	    self.lasttag = '???'
	    self.nomoretags = 0
	    self.literal = 0
	    self._normfunc = lambda s: s
	    self._strict = 0

	def close(self):
	    self.goahead(1)

	def feed(self, data):
	    self.rawdata = self.rawdata + data
	    self.goahead(0)

	def normalize(self, norm):
	    prev = ((self._normfunc is string.lower) and 1) or 0
	    self._normfunc = (norm and string.lower) or (lambda s: s)
	    return prev

	def restrict(self, strict):
	    prev = self._strict
	    self._strict = (strict and 1) or 0
	    return prev

	# Internal -- handle data as far as reasonable.  May leave state
	# and data to be processed by a subsequent call.  If 'end' is
	# true, force handling all data as if followed by EOF marker.
	def goahead(self, end):
	    rawdata = self.rawdata
	    i = 0
	    n = len(rawdata)
	    while i < n:
		if self.nomoretags:
		    self.lex_data(rawdata[i:n])
		    i = n
		    break
		j = interesting.search(rawdata, i)
		if j < 0: j = n
		if i < j: self.lex_data(rawdata[i:j])
		i = j
		if i == n: break
		if rawdata[i] == '<':
		    if starttagopen.match(rawdata, i) >= 0:
			if self.literal:
			    self.lex_data(rawdata[i])
			    i = i+1
			    continue
			k = self.parse_starttag(i)
			if k < 0: break
			i = k
			continue
		    if endtagopen.match(rawdata, i) >= 0:
			k = self.parse_endtag(i)
			if k < 0: break
			i =  k
			self.literal = 0
			continue
		    if commentopen.match(rawdata, i) >= 0:
			if self.literal:
			    self.lex_data(rawdata[i])
			    i = i+1
			    continue
			k = self.parse_comment(i)
			if k < 0: break
			i = i+k
			continue
		    k = processinginstruction.match(rawdata, i)
		    if k >= 0:
			#  Processing instruction:
			if self._strict:
			    self.lex_pi(processinginstruction.group(1))
			    i = i + k
			else:
			    self.lex_data(rawdata[i])
			    i = i + 1
			continue
		    k = special.match(rawdata, i)
		    if k >= 0:
			#  Markup declaration:
			if self.literal:
			    self.lex_data(rawdata[i])
			    i = i+1
			    continue
			i = i+k
			continue
		elif rawdata[i] == '&':
		    charref = (self._strict and legalcharref) or simplecharref
		    k = charref.match(rawdata, i)
		    if k >= 0:
			k = i+k
			if rawdata[k-1] not in ';\n': k = k-1
			name = charref.group(1)[:-1]
			if name[0] in '0123456789':
			    #  Character reference:
			    self.lex_charref(string.atoi(name))
			else:
			    #  Named character reference:
			    self.lex_namedcharref(self._normfunc(name))
			i = k
			continue
		    k = entityref.match(rawdata, i)
		    if k >= 0:
			#  General entity reference:
			k = i+k
			if rawdata[k-1] != ';': k = k-1
			name = entityref.group(1)
			self.lex_entityref(name)
			i = k
			continue
		else:
		    raise RuntimeError, 'neither < nor & ??'
		# We get here only if incomplete matches but
		# nothing else
		k = incomplete.match(rawdata, i)
		if k < 0:
		    self.lex_data(rawdata[i])
		    i = i+1
		    continue
		j = i+k
		if j == n:
		    break # Really incomplete
		self.lex_data(rawdata[i:j])
		i = j
	    # end while
	    if end and i < n:
		self.lex_data(rawdata[i:n])
		i = n
	    self.rawdata = rawdata[i:]
	    # XXX if end: check for empty stack

	# Internal -- parse comment, return length or -1 if not terminated
	def parse_comment(self, i):
	    rawdata = self.rawdata
	    if rawdata[i:i+4] <> '<!--':
		raise RuntimeError, 'unexpected call to parse_comment'
	    if not self._strict:
		j = commentclose.search(rawdata, i+4)
		if j < 0:
		    return -1
		self.lex_comment(rawdata[i+4: j])
		j = j+commentclose.match(rawdata, j)
		q = j - i
	    else:
		# stricter parsing; this requires legal SGML:
		q = legalcomment.match(rawdata, i)
		if q < 0:
		    return -1
		cmtdata = legalcomment.group(1)
		print 'commentdata =', `cmtdata`
		while 1:
		    len = comment.match(cmtdata)
		    if len >= 0:
			self.lex_comment(comment.group(1))
			cmtdata = cmtdata[len:]
		    else:
			break
	    return q

	# Internal -- handle starttag, return length or -1 if not terminated
	def parse_starttag(self, i):
	    rawdata = self.rawdata
	    if shorttagopen.match(rawdata, i) >= 0:
		# SGML shorthand: <tag/data/ == <tag>data</tag>
		# XXX Can data contain &... (entity or char refs)?
		# XXX Can data contain < or > (tag characters)?
		# XXX Can there be whitespace before the first /?
		j = shorttag.match(rawdata, i)
		if j < 0:
		    return -1
		tag, data = shorttag.group(1, 2)
		tag = self._normfunc(tag)
		self.finish_shorttag(tag, data)
		k = i+j
		if rawdata[k-1] == '<':
		    k = k-1
		return k
	    # XXX The following should skip matching quotes (' or ")
	    j = endbracket.search(rawdata, i+1)
	    if j < 0:
		return -1
	    # Now parse the data between i+1 and j into a tag and attrs
	    attrs = []
	    if rawdata[i:i+2] == '<>':
		# SGML shorthand: <> == <last open tag seen>
		k = j
		tag = self.lasttag
	    else:
		k = tagfind.match(rawdata, i+1)
		if k < 0:
		    raise RuntimeError, 'unexpected call to parse_starttag'
		k = i+1+k
		tag = self._normfunc(rawdata[i+1:k])
		self.lasttag = tag
	    while k < j:
		l = attrfind.match(rawdata, k)
		if l < 0: break
		attrname, rest, attrvalue = attrfind.group(1, 2, 3)
		if not rest:
		    attrvalue = attrname
		elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
		     attrvalue[:1] == '"' == attrvalue[-1:]:
		    attrvalue = attrvalue[1:-1]
		attrs.append((self._normfunc(attrname), attrvalue))
		k = k + l
	    if rawdata[j] == '>':
		j = j+1
	    self.lex_starttag(tag, attrs)
	    return j

	# Internal -- parse endtag
	def parse_endtag(self, i):
	    rawdata = self.rawdata
	    j = endbracket.search(rawdata, i+1)
	    if j < 0:
		return -1
	    tag = self._normfunc(string.strip(rawdata[i+2:j]))
	    if rawdata[j] == '>':
		j = j+1
	    self.lex_endtag(tag)
	    return j


if not _sgmllex:
    # Regular expressions used for parsing:
    interesting = regex.compile('[&<]')
    incomplete = regex.compile('&\([a-zA-Z][a-zA-Z0-9]*\|#[0-9]*\)?\|'
			       '<\([a-zA-Z][^<>]*\|'
			       '/\([a-zA-Z][^<>]*\)?\|'
			       '![^<>]*\)?')

    entityref = regex.compile('&\([a-zA-Z][a-zA-Z0-9]*\)[^a-zA-Z0-9]')
    simplecharref = regex.compile('&#\([0-9]+[^0-9]\)')
    legalcharref = regex.compile('&#\([0-9]+[^0-9]\|[a-zA-Z.-]+[^a-zA-Z.-]\)')
    processinginstruction = regex.compile('<\?\([^>]*\)>')

    starttagopen = regex.compile('<[>a-zA-Z]')
    shorttagopen = regex.compile('<[a-zA-Z][a-zA-Z0-9]*/')
    shorttag = regex.compile('<\([a-zA-Z][a-zA-Z0-9]*\)/\([^/]*\)/')
    endtagopen = regex.compile('</[<>a-zA-Z]')
    endbracket = regex.compile('[<>]')
    special = regex.compile('<![^>]*>')
    commentopen = regex.compile('<!--')
    legalcomment = regex.compile('<!\(\(--\([^-]\|-[^-]\)*--[ \t\n]*\)*\)>')
    comment = regex.compile('--\(\([^-]\|-[^-]\)*\)--[ \t\n]*')
    commentclose = regex.compile('--[ \t\n]*>')
    tagfind = regex.compile('[a-zA-Z][a-zA-Z0-9]*')
    attrfind = regex.compile( \
	'[ \t\n]+\([a-zA-Z_][a-zA-Z_0-9]*\)'
	'\([ \t\n]*=[ \t\n]*'
	'\(\'[^\']*\'\|"[^"]*"\|[-a-zA-Z0-9./:+*%?!()_#=]*\)\)?')


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
