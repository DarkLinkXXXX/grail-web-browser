"""A parser for SGML, using the derived class as static DTD.


"""
__version__ = "$Revision: 1.15 $"
# $Source: /home/john/Code/grail/src/sgml/SGMLParser.py,v $

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


import SGMLLexer
SGMLError = SGMLLexer.SGMLError
import string


# SGML parser class -- find tags and call handler functions.
# Usage: p = SGMLParser(); p.feed(data); ...; p.close().
# The dtd is defined by deriving a class which defines methods
# with special names to handle tags: start_foo and end_foo to handle
# <foo> and </foo>, respectively, or do_foo to handle <foo> by itself.


class SGMLParser(SGMLLexer.SGMLLexer):

    doctype = ''			# 'html', 'sdl', ...

    def __init__(self, verbose = 0):
	self.verbose = verbose
	self._tag_methods = {}
	SGMLLexer.SGMLLexer.__init__(self)

    def close(self):
	SGMLLexer.SGMLLexer.close(self)
	while self.stack:
	    self.lex_endtag(self.stack[-1])
	# Clean out circular references:
	for k in self._tag_methods.keys():
	    del self._tag_methods[k]
	self._tag_methods = None
	if hasattr(self, '_l'):
	    self._l.data_cb = _dummy_data_handler

    # Interface -- reset this instance.  Loses all unprocessed data.
    def reset(self):
	SGMLLexer.SGMLLexer.reset(self)
	self.normalize(1)		# normalize NAME token to lowercase
	self.restrict(1)		# impose user-agent compatibility
	self.omittag = 1		# default to HTML style
	self.stack = []
	self.cdata = 0

    def get_stack(self):
	"""Return current context stack.

	This allows tag implementations to examine their context.
	"""
	return tuple(self.stack)

    #  The following methods are the interface subclasses need to
    #  override to support any special handling of tags, data, or
    #  anomalous conditions.

    # Example -- handle entity reference, no need to override
    entitydefs = \
	       {'lt': '<', 'gt': '>', 'amp': '&', 'quot': '"'}

    def handle_entityref(self, name, terminator):
	table = self.entitydefs
	if table.has_key(name):
	    self.handle_data(table[name])
	else:
	    self.unknown_entityref(name, terminator)


    def handle_data(self, data):
	"""
	"""
	pass

    def handle_endtag(self, tag, method):
	"""
	"""
	method()

    def handle_starttag(self, tag, method, attributes):
	"""
	"""
	method(attributes)

    def unknown_charref(self, ordinal, terminator):
	"""
	"""
	pass

    def unknown_endtag(self, tag):
	"""
	"""
	pass

    def unknown_entityref(self, ref, terminator):
	"""
	"""
	pass

    def unknown_namedcharref(self, ref, terminator):
	"""
	"""
	pass

    def unknown_starttag(self, tag, attrs):
	"""
	"""
	pass

    def report_unbalanced(self, tag):
	"""
	"""
	pass


    #  The remaining methods are the internals of the implementation and
    #  interface with the lexer.  Subclasses should rarely need to deal
    #  with these.

    # For derived classes only -- enter literal mode (CDATA)
    def setliteral(self, *args):
	self.cdata = 1 #@@ finish implementing this...

    def lex_data(self, data):
	self.handle_data(data)

    def set_data_handler(self, handler):
	self.handle_data = handler
	if hasattr(self, '_l'):
	    self._l.data_cb = handler


    def _load_tag_handlers(self, tag):
	try:
	    start = getattr(self, 'start_' + tag)
	except AttributeError:
	    start = end = do = None
	    if hasattr(self, 'do_' + tag):
		do = getattr(self, 'do_' + tag)
	else:
	    end = do = None
	    if hasattr(self, 'end_' + tag):
		end = getattr(self, 'end_' + tag)
	tuple = start, end, do
	self._tag_methods[tag] = tuple
	return tuple

    def lex_starttag(self, tag, attrs):
	#print 'received start tag', `tag`
	if not tag:
	    if self.omittag and self.stack:
		tag = self.lasttag
	    elif not self.omittag:
		self.lex_endtag('')
		return
	    elif not self.stack:
		tag = self.doctype
		if not tag:
		    raise SGMLError, \
			  'Cannot start the document with an empty tag.'
	if not self._tag_methods.has_key(tag):
	    start, end, do = self._load_tag_handlers(tag)
	else:
	    start, end, do = self._tag_methods[tag]

	if do:
	    self.handle_starttag(tag, do, attrs)
	elif start:
	    self.lasttag = tag
	    self.handle_starttag(tag, start, attrs)
	    self.stack.append(tag)
	else:
	    self.unknown_starttag(tag, attrs)

    def lex_endtag(self, tag):
	stack = self.stack
	if not tag:
	    found = len(stack) - 1
	    if found < 0:
		self.report_unbalanced(tag)
		return
	else:
	    if tag not in stack:
		self.report_unbalanced(tag)
		return
	    for i in range(len(stack)):
		if stack[i] == tag: found = i
	while len(stack) > found:
	    tag = stack[-1]
	    start, end, do = self._tag_methods[tag]
	    if end:
		self.handle_endtag(tag, end)
	    else:
		self.unknown_endtag(tag)
	    del stack[-1]


    named_characters = {'re' : '\r',
			'rs' : '\n',
			'space' : ' '}

    def lex_namedcharref(self, name, terminator):
	if self.named_characters.has_key(name):
	    self.handle_data(self.named_characters[name])
	else:
	    self.unknown_namedcharref(name, terminator)

    def lex_charref(self, ordinal, terminator):
	if 0 < ordinal < 256:
	    self.handle_data(chr(ordinal))
	else:
	    self.unknown_charref(ordinal, terminator)

    def lex_entityref(self, name, terminator):
	self.handle_entityref(name, terminator)


def _dummy_data_handler(data):
    """Dummy handler used in clearing circular references.
    """
    pass


#  The test code is now located in test_parser.py.
