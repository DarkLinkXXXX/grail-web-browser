# $Id: SGMLParser.py,v 1.1 1996/03/14 22:57:18 fdrake Exp $
"""A lexer, parser for SGML, using the derived class as static DTD.

This only supports those SGML features used by HTML.
See W3C tech report: 'A lexical analyzer for HTML and Basic SGML'
http://www.w3.org/pub/WWW/MarkUp/SGML/sgml-lex/sgml-lex.html
"""
# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


from SGMLLexer import SGMLLexer, SGMLError


# SGML parser class -- find tags and call handler functions.
# Usage: p = SGMLParser(); p.feed(data); ...; p.close().
# The dtd is defined by deriving a class which defines methods
# with special names to handle tags: start_foo and end_foo to handle
# <foo> and </foo>, respectively, or do_foo to handle <foo> by itself.
# (Tags are converted to lower case for this purpose.)
# XXX what about periods, hyphens in tag names?

class SGMLParser(SGMLParserBase):

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

	def lex_starttag(self, tag, attrs):
	    attrs = attrs.items()	# map to list of tuples for now
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
	    if not tag:
		found = len(self.stack) - 1
		if found < 0:
		    self.unknown_endtag(tag)
		    return
	    else:
		if tag not in self.stack:
		    try:
			method = getattr(self, 'end_' + tag)
		    except AttributeError:
			self.unknown_endtag(tag)
		    return
		found = len(self.stack)
		for i in range(found):
		    if self.stack[i] == tag: found = i
	    while len(self.stack) > found:
		tag = self.stack[-1]
		try:
		    method = getattr(self, 'end_' + tag)
		except AttributeError:
		    method = None
		if method:
		    self.handle_endtag(tag, method)
		else:
		    self.unknown_endtag(tag)
		del self.stack[-1]


	named_characters = {'re' : '\r',
			    'rs' : '\n',
			    'space' : ' '}

	def lex_namedcharref(self, name):
	    if self.named_characters.has_key(name):
		handle_data(self._named_characters[name])
	    else:
		self.unknown_namedcharref(name)


	#  Theref following methods are the interface subclasses need to
	#  override to support any special handling.

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
