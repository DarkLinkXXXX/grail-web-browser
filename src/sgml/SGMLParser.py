# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""A parser for SGML, using the derived class as static DTD.


"""
__version__ = "$Revision: 1.20 $"
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

    doctype = ''			# 'html', 'sdl', '...'

    def __init__(self, verbose = 0):
	self.verbose = verbose
	self.__taginfo = {}
	SGMLLexer.SGMLLexer.__init__(self)

    def close(self):
	SGMLLexer.SGMLLexer.close(self)

    # This is called by the lexer after the document has been fully processed;
    # needed to clean out circular references and empty the stack.
    def cleanup(self):
	while self.stack:
	    self.lex_endtag(self.stack[-1])
	self.__taginfo = {}
	self.set_data_handler(_dummy_data_handler)
	SGMLLexer.SGMLLexer.cleanup(self)

    # Interface -- reset this instance.  Loses all unprocessed data.
    def reset(self):
	SGMLLexer.SGMLLexer.reset(self)
	self.normalize(1)		# normalize NAME token to lowercase
	self.restrict(1)		# impose user-agent compatibility
	self.omittag = 1		# default to HTML style
	self.stack = []

    def get_stack(self):
	"""Return current context stack.

	This allows tag implementations to examine their context.
	"""
	result = []
	for ti in self.stack:
	    result.append(ti.tag)
	return tuple(result)

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
	method(self)

    def handle_starttag(self, tag, method, attributes):
	"""
	"""
	method(self, attributes)

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

    def lex_data(self, data):
	self.handle_data(data)

    def set_data_handler(self, handler):
	self.handle_data = handler
	if hasattr(self, '_l'):
	    self._l.data_cb = handler
	self.lex_data = handler

    def get_taginfo(self, tag):
	start = do = end = None
	klass = self.__class__
	if hasattr(klass, "start_" + tag):
	    start = getattr(klass, "start_" + tag)
	    if hasattr(klass, "end_" + tag):
		end = getattr(klass, "end_" + tag)
	elif hasattr(klass, "do_" + tag):
	    do = getattr(klass, "do_" + tag)
	if start or do:
	    return TagInfo(tag, start, do, end)

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
	if self.__taginfo.has_key(tag):
	    taginfo = self.__taginfo[tag]
	else:
	    taginfo = self.get_taginfo(tag)
	    self.__taginfo[tag] = taginfo
	if not taginfo:
	    self.unknown_starttag(tag, attrs)
	elif taginfo.container:
	    self.lasttag = tag
	    self.handle_starttag(tag, taginfo.start, attrs)
	    self.stack.append(taginfo)
	else:
	    self.handle_starttag(tag, taginfo.start, attrs)
	    self.handle_endtag(tag, taginfo.end)

    def lex_endtag(self, tag):
	stack = self.stack
	if tag:
	    found = None
	    for i in range(len(stack)):
		if stack[i].tag == tag:
		    found = i
	    if found is None:
		self.report_unbalanced(tag)
		return
	else:
	    found = len(stack) - 1
	    if found < 0:
		self.report_unbalanced(tag)
		return
	while len(stack) > found:
	    taginfo = stack[-1]
	    self.handle_endtag(taginfo.tag, taginfo.end)
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


from types import StringType

class TagInfo:
    as_dict = 1
    container = 1

    def __init__(self, tag, start, do, end):
	self.tag = tag
	if start:
	    self.start = start
	    self.end = end or _nullfunc
	else:
	    self.container = 0
	    self.start = do
	    self.end = _nullfunc

    def __cmp__(self, other):
	if type(other) is StringType:
	    return cmp(self.tag, other)
	if type(other) is type(self):
	    return cmp(self.tag, other.tag)
	raise TypeError, "incomparable values"


def _nullfunc(*args, **kw):
    # Dummy end tag handler for situations where no handler is provided
    # or allowed.
    pass


def _dummy_data_handler(data):
    # Dummy handler used in clearing circular references.
    pass


#  The test code is now located in test_parser.py.
