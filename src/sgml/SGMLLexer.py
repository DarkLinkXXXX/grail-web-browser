"""A lexer for SGML, using derived classes as parser and DTD.

This module provides a transparent interface allowing the use of W3C's
sgmllex module or a python-only module for installations which do not
have W3C's parser or which need to modify the concrete syntax
recognized by the lexer.

For information on W3C's lexer, please refer to the W3C tech report:
'A lexical analyzer for HTML and Basic SGML'
http://www.w3.org/pub/WWW/MarkUp/SGML/sgml-lex/sgml-lex.html
"""
__version__ = "$Revision: 1.13 $"
# $Source: /home/john/Code/grail/src/sgml/SGMLLexer.py,v $


#  These constants are not used in this module, but are provided to
#  allow other modules to know about the concrete syntax we support.

COM = "--"				# comment start or end
CRO = "&#"				# character reference open
REFC = ";"				# reference close
DSO = "["				# declaration subset open
DSC = "]"				# declaration subset close
ERO = "&"				# entity reference open
LIT = '"'				# literal start or end
LITA = "'"				# literal start or end (alternative)
MDO = "<!"				# markup declaration open
MDC = ">"				# markup declaration close
MSC = "]]"				# marked section close
NET = "/"				# null end tag
PIO = "<?"				# processing instruciton open
PIC = ">"				# processing instruction close
STAGO = "<"				# start tag open
ETAGO = "</"				# end tag open
TAGC = ">"				# tag close
VI = "="				# value indicator


# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).

import sys

try:
    import sgmllex # compiled flex scanner
except ImportError:
    import regex
    _sgmllex = 0
    sys.stderr.write("Guido's parser\n")
else:
    _sgmllex = 1
    sys.stderr.write("Connolly's parser\n")

import string


SGMLError = 'SGMLLexer.SGMLError'


# SGML lexer base class -- find tags and call handler functions.
# Usage: p = SGMLLexer(); p.feed(data); ...; p.close().
# The data between tags is passed to the parser by calling
# self.lex_data() with some data as argument (the data may be split up
# in arbutrary chunks).  Entity references are passed by calling
# self.lex_entityref() with the entity reference as argument.


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

    def lex_charref(self, ordinal, terminator):
	"""Process a numeric character reference.
	"""
	pass

    def lex_namedcharref(self, refname, terminator):
	"""Process a named character reference.
	"""
	pass

    def lex_entityref(self, refname, terminator):
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

	`declaration_info' will be a list of strings.  The first will
	be the name of the declaration (doctype, etc.), followed by each
	additional name, nametoken, quoted literal, or comment in the
	declaration.  Literals and comments will include the quotation
	marks or comment delimiters to allow the client to process each
	correctly.  Normalization of names and nametokens will be handled
	as for general identifiers.
	"""
	pass


class SGMLLexer(SGMLLexerBase):
    nomoretags = 0

    if _sgmllex:
	def __init__(self):
	    self.reset()
	    self.feed = self.feed

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
				      self._lex_declaration,
				      self._lex_err)

	def restrict(self, constrain):
	    self._l.compat(constrain)
	    return self._l.restrict(constrain)

	def close(self):
	    """Flush any remaining data in the lexer's internal buffer.
	    """
	    self._l.scan('')

	def setnomoretags(self):
	    self._l.scan('')		# flush flex cache - not perfect
	    self.feed = self.lex_data
	    self.nomoretags = 1

	def _lex_got_geref(self, entname, terminator):
	    if self.nomoretags:
		self.lex_data('&%s%s' % (entname, terminator))
	    else:
		self.lex_entityref(entname[1:], terminator)

	def _lex_got_namedcharref(self, name, terminator):
	    self.lex_namedcharref(name[2:], terminator)

	def _lex_got_endtag(self, tagname):
	    if self.nomoretags:
		self.lex_data('</%s>' % tagname)
	    else:
		self.lex_endtag(tagname[2:])

	def _lex_got_starttag(self, name, attributes):
	    for k, v in attributes.items():
		if v and '&' in v:
		    from SGMLReplacer import replace
		    attributes[k] = replace(v, self.entitydefs)
	    self.lex_starttag(name[1:], attributes)

	def _lex_declaration(self, types, strings):
	    if len(types) > 1 and types[1] is sgmllex.comment:
		# strip of leading/trailing --
		map(lambda s,f=self.lex_comment: f(s[2:-2]), strings[1:-1])

	    elif types[0] is sgmllex.processingInstruction:
		# strip <? and >
		self.lex_pi(strings[0][2:-1])
	    else:
		#XXX other markup declarations
		self.lex_declaration([strings[0][2:]]
				     + map(None, strings[1:-1]))

	def _lex_err(self, types, strings):
	    #  raise SGMLError?
	    pass

    else:				# sgmllex not available

	def __init__(self):
	    self.reset()

	def reset(self):
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

	def restrict(self, constrain):
	    prev = not self._strict
	    self._strict = not ((constrain and 1) or 0)
	    return prev

	def setnomoretags(self):
	    self.nomoretags = 1

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
			if self._strict:
			    if rawdata[i+2] in string.letters:
				k = self.parse_declaration(i)
				if k > -1:
				    i = k
			    else:
				self.lex_data('<!')
				i = i + 2
			else:
			    #  Pretend it's a arkup declaration:
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
			if rawdata[k-1] not in ';\n':
			    k = k-1
			    terminator = ''
			else:
			    terminator = rawdata[k-1]
			name = charref.group(1)[:-1]
			if name[0] in '0123456789':
			    #  Character reference:
			    self.lex_charref(string.atoi(name), terminator)
			else:
			    #  Named character reference:
			    self.lex_namedcharref(self._normfunc(name),
						  terminator)
			i = k
			continue
		    k = entityref.match(rawdata, i)
		    if k >= 0:
			#  General entity reference:
			k = i+k
			if rawdata[k-1] not in ';\n':
			    k = k-1
			    terminator = ''
			else:
			    terminator = rawdata[k-1]
			name = entityref.group(1)
			self.lex_entityref(name, terminator)
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
	    if rawdata[i:i+4] <> (MDO + COM):
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
		# XXX Can data contain &... (entity or char refs)? ... yes
		# XXX Can data contain < or > (tag characters)?
		# XXX Can there be whitespace before the first /?
		j = shorttag.match(rawdata, i)
		if j < 0:
		    self.lex_data(rawdata[i])
		    return i + 1
		tag, data = shorttag.group(1, 2)
		tag = self._normfunc(tag)
		self.lex_starttag(tag, {})
		self.lex_data(data)
		self.lex_endtag(tag)
		return i + j
	    # XXX The following should skip matching quotes (' or ")
	    j = endbracket.search(rawdata, i+1)
	    if j < 0:
		return -1
	    # Now parse the data between i+1 and j into a tag and attrs
	    attrs = {}
	    if rawdata[i:i+2] == '<>':
		#  Semantics of the empty tag are handled by lex_starttag():
		if self._strict:
		    self.lex_starttag('', {})
		    return i + 2
		else:
		    self.lex_data(rawdata[i])
		    return i + 1

	    k = tagfind.match(rawdata, i+1)
	    if k < 0:
		raise RuntimeError, 'unexpected call to parse_starttag'
	    k = i+1+k
	    tag = self._normfunc(rawdata[i+1:k])
	    #self.lasttag = tag
	    while k < j:
		l = attrfind.match(rawdata, k)
		if l < 0: break
		attrname, rest, attrvalue = attrfind.group(1, 2, 3)
		if not rest:
		    attrvalue = None	# was:  = attrname
		elif attrvalue[:1] == LITA == attrvalue[-1:] or \
		     attrvalue[:1] == LIT == attrvalue[-1:]:
		    attrvalue = attrvalue[1:-1]
		    if '&' in attrvalue:
			from SGMLReplacer import replace
			attrvalue = replace(attrvalue, self.entitydefs)
		attrs[self._normfunc(attrname)] = attrvalue
		k = k + l
	    if rawdata[j] == '>':
		j = j+1
	    self.lex_starttag(tag, attrs)
	    return j

	# Internal -- parse endtag
	def parse_endtag(self, i):
	    rawdata = self.rawdata
	    j = endtag.match(rawdata, i)
	    if j < 3:
		ch = rawdata[i+2]
		if ch == STAGO:
		    if self._strict:
			self.lex_endtag('')
			return i + 2
		elif ch == TAGC:
		    if self._strict:
			self.lex_endtag('')
			return i + 3
		self.lex_data(rawdata[i])
		return i + 1
	    j = i + j - 1
	    if rawdata[j] == '>':
		j = j+1
	    self.lex_endtag(self._normfunc(endtag.group(1)))
	    return j

	def parse_declaration(self, i):
	    #  This only gets used in "strict" mode.
	    rawdata = self.rawdata
	    #  Markup declaration, possibly illegal:
	    strs = []
	    i = i + 2
	    k = md_name.match(rawdata, i)
	    strs.append(self._normfunc(md_name.group(1)))
	    i = i + k
	    while k > 0:
		#  Have to check the comment pattern first so we don't get
		#  confused and think this is a name that starts with '--':
		k = comment.match(rawdata, i)
		if k > 0:
		    strs.append(string.strip(comment.group(0)))
		    i = i + k
		    continue
		k = md_name.match(rawdata, i)
		if k > 0:
		    strs.append(self._normfunc(md_name.group(1)))
		    i = i + k
		    continue
		k = md_string.match(rawdata, i)
		if k > 0:
		    strs.append(md_string.group(1)[1:-1])
		    i = i + k
		    continue
	    k = string.find(rawdata, '>', i)
	    if k >= 0:
		i = k + 1
	    self.lex_declaration(strs)
	    return i


if not _sgmllex:
    # Regular expressions used for parsing:
    interesting = regex.compile('[&<]')
    incomplete = regex.compile('&\([a-zA-Z][a-zA-Z0-9]*\|#[0-9]*\)?\|'
			       '<\([a-zA-Z][^<>]*\|'
			       '/\([a-zA-Z][^<>]*\)?\|'
			       '![^<>]*\)?')

    entityref = regex.compile(ERO + '\([a-zA-Z][-.a-zA-Z0-9]*\)[^-.a-zA-Z0-9]')
    simplecharref = regex.compile(CRO + '\([0-9]+[^0-9]\)')
    legalcharref \
	= regex.compile(CRO + '\([0-9]+[^0-9]\|[a-zA-Z.-]+[^a-zA-Z.-]\)')
    processinginstruction = regex.compile('<\?\([^>]*\)' + PIC)

    starttagopen = regex.compile(STAGO + '[>a-zA-Z]')
    shorttagopen = regex.compile(STAGO + '[a-zA-Z][a-zA-Z0-9.-]*[ \t\n\r]*'
				 + NET)
    shorttag = regex.compile(STAGO + '\([a-zA-Z][a-zA-Z0-9.-]*\)[ \t\n\r]*'
			     + NET + '\([^/]*\)' + NET)
    endtagopen = regex.compile(ETAGO + '[<>a-zA-Z]')
    endbracket = regex.compile('[<>]')
    endtag = regex.compile(ETAGO +
			   '\([a-zA-Z][-.a-zA-Z0-9]*\)'
			   '\([^-.<>a-zA-Z0-9]?[^<>]*\)[<>]')
    special = regex.compile(MDO + '[^>]*' + MDC)
    markupdeclaration = regex.compile(MDO +
				      '\(\([-.a-zA-Z0-9]+\|'
				      + LIT + '[^"]*' + LIT + '\|'
				      + LITA + "[^']*" + LITA + '\|'
				      + COM + '\([^-]\|-[^-]\)*' + COM
				      + '\)[ \t\n\r]*\)*' + MDC)
    md_name = regex.compile('\([^> \n\t\r\'"]+\)[ \n\t\r]*')
    md_string = regex.compile('\("[^"]*"\|\'[^\']*\'\)[ \n\t\r]*')
    commentopen = regex.compile(MDO + COM)
    legalcomment = regex.compile(MDO + '\(\(' + COM + '\([^-]\|-[^-]\)*'
				 + COM + '[ \t\n]*\)*\)' + MDC)
    comment = regex.compile(COM + '\(\([^-]\|-[^-]\)*\)' + COM + '[ \t\n]*')
    commentclose = regex.compile(COM + '[ \t\n]*' + MDC)
    tagfind = regex.compile('[a-zA-Z][a-zA-Z0-9.-]*')
    attrfind = regex.compile( \
	'[ \t\n]+\([a-zA-Z][a-zA-Z_0-9.-]*\)'
	'\([ \t\n]*' + VI + '[ \t\n]*'
	'\(\\' + LITA + '[^\']*\\' + LITA
	+ '\|' + LIT + '[^"]*' + LIT + '\|[-a-zA-Z0-9./:+*%?!()_#=]*\)\)?')


#  Test code for the lexer is now located in the test_lexer.py script.
