# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

import sys
import os
import string
import time
import urlparse

import Outliner
import SGMLParser


True = 1
False = None


class Error:
    def __init__(self, filename):
	self.filename = filename
    def __repr__(self):
	return "<%s for file %s>" % (self.__class__.__name__, self.filename)

class BookmarkFormatError(Error):
    def __init__(self, filename, problem):
	Error.__init__(self, filename)
	self.problem = problem

class PoppedRootError(Error):
    pass


class BookmarkNode(Outliner.OutlinerNode):
    """Bookmarks are represented internally as a tree of nodes containing
    relevent information.

    Methods:

      title()         -- return title
      uri()           -- return URI string
      add_date()      -- return bookmark add timestamp
      last_modified() -- return last modified timestamp
      last_visited()  -- return last visited timestamp
      description()   -- return description string

        [[self explanatory??]]

      set_title(title)
      set_uri(uri_string)
      set_add_date(seconds)
      set_last_modified(seconds)
      set_last_visited(seconds)
      set_description(string)

    Instance variables:

      No Public Ivars
    """
    _uri = ''
    _islink_p = False
    _isseparator_p = False

    def __init__(self, title='', uri_string = None,
		 add_date=None, last_visited=None,
		 last_modified=None, description=''):
	self._children = []		# performance hack; should call base
	self._title = title
	if uri_string:
	    self._uri = uri_string
	    self._islink_p = True
	self._desc = description
	t = time.time()
	self._add_date = add_date or t
	self._visited = last_visited or t
	self._modified = last_modified
	self._leaf_p = uri_string or last_visited

    def __repr__(self):
	return Outliner.OutlinerNode.__repr__(self) + ' ' + self.title()
    def leaf_p(self): return self._leaf_p

    def clone(self):
	newnode = BookmarkNode(self._title, self._uri, self._add_date,
			       self._visited, self._desc)
	# TBD: no good way to do this
	newnode._expanded_p = self._expanded_p
	newnode._depth = self._depth
	for child in self._children:
	    newchild = child.clone()
	    newchild._parent = newnode
	    newnode._children.append(newchild)
	# set derived class attributes
	newnode._islink_p = self._islink_p
	newnode._isseparator_p = self._isseparator_p
	newnode._leaf_p = self._leaf_p
	return newnode

    def append_child(self, node):
	Outliner.OutlinerNode.append_child(self, node)
	self._leaf_p = False
    def insert_child(self, node, index):
	Outliner.OutlinerNode.insert_child(self, node, index)
	self._leaf_p = False
    def del_child(self, node):
	rtnnode = Outliner.OutlinerNode.del_child(self, node)
	if self._islink_p and len(self._children) == 0:
	    self._leaf_p = True
	return rtnnode

    def title(self): return self._title
    def uri(self): return self._uri
    def add_date(self): return self._add_date
    def last_modified(self): return self._modified
    def last_visited(self): return self._visited
    def description(self): return self._desc
    def islink_p(self): return self._islink_p
    def isseparator_p(self): return self._isseparator_p

    def get_normurl(self):
	scheme, netloc, path, params, query, fragment \
		= urlparse.urlparse(self.uri())
	return urlparse.urlunparse((scheme, string.lower(netloc), path,
				    params, query, ''))

    def set_separator(self):
	self._isseparator_p = True
	self._leaf_p = True
	self._title = '------------------------------'

    def set_title(self, title=''): self._title = string.strip(title)
    def set_add_date(self, add_date=time.time()): self._add_date = add_date
    def set_last_visited(self, lastv):
	self._visited = lastv
	self._leaf_p = True
    def set_last_modified(self, lastm):
	self._modified = lastm
	self._leaf_p = True

    def set_description(self, description=''):
	self._desc = string.strip(description)
    def set_uri(self, uri_string=''):
	self._uri = string.split(uri_string)
	if self._uri:
	    self._islink_p = True
	    self._leaf_p = True



class HTMLBookmarkReader:
    def __init__(self, parser):
	self._parser = parser

    def read_file(self, fp):
	self._parser.feed(fp.read())
	return self._parser._root



class NetscapeBookmarkParser(SGMLParser.SGMLParser):
    _root = None
    _current = None
    _prevleaf = None
    _store_node = None
    _storing = 0
    _buffer = ''

    from htmlentitydefs import entitydefs

    def __init__(self, filename):
	self._filename = filename
	SGMLParser.SGMLParser.__init__(self)

    def save_bgn(self):
	self._buffer = ''

    def save_end(self):
	s, self._buffer = self._buffer, ''
	return s

    def handle_data(self, data):
	self._buffer = self._buffer + data

    def handle_starttag(self, tag, method, attrs):
	method(attrs)

    def _push_new(self):
	if not self._current:
	    raise BookmarkFormatError(self._filename, 'file corrupted')
	newnode = BookmarkNode()
	self._current.append_child(newnode)
	self._current = newnode

    def start_h1(self, attrs):
	self._root = self._current = BookmarkNode()
	self.save_bgn()

    def end_h1(self):
	self._current.set_title(self.save_end())

    def start_h3(self, attrs):
	self._push_new()
	self.save_bgn()
	if attrs.has_key('add_date'):
	    self._current.set_add_date(string.atoi(attrs['add_date']))
	if attrs.has_key('folded'):
	    self._current.collapse()

    def end_h3(self):
	self.end_h1()
	self._store_node = self._current

    def do_hr(self, attrs):
	snode = BookmarkNode()
	snode.set_separator()
	self._current.append_child(snode)

    def end_dl(self):
	if not self._current: raise PoppedRootError(self._filename)
	self.ddpop()
	self._current = self._current.parent()

    def do_dd(self, attrs):
	self.save_bgn()
	self._storing = 1

    def ddpop(self, *args):
	if self._store_node:
	    self._store_node.set_description(self.save_end())
	    self._store_node = None

    do_dt = ddpop
    start_dl = ddpop

    def start_a(self, attrs):
	self._push_new()
	self.save_bgn()
	curnode = self._current		# convenience
	if attrs.has_key('href'):
	    curnode.set_uri(attrs['href'])
	if attrs.has_key('add_date'):
	    curnode.set_add_date(string.atoi(attrs['add_date']))
	if attrs.has_key('last_modified'):
	    curnode.set_last_modified(string.atoi(attrs['last_modified']))
	if attrs.has_key('last_visit'):
	    curnode.set_last_visited(string.atoi(attrs['last_visit']))

    def end_a(self):
	self._current.set_title(self.save_end())
	self._prevleaf = self._store_node = self._current
	self._current = self._current.parent()


def _prepstring(s):
    # return "HTML safe" copy of a string
    i = string.find(s, '&')
    while i >= 0:
	s = "%s&amp;%s" % (s[:i], s[i + 1:])
	i = string.find(s, '&', i + 3)
    i = string.find(s, '<')
    while i >= 0:
	s = "%s&lt;%s" % (s[:i], s[i + 1:])
	i = string.find(s, '<', i + 2)
    return s


class NetscapeBookmarkWriter:
    def _tab(self, node): return ' ' * (4 * node.depth())

    def _write_description(self, desc):
	if not desc: return
	# write the description, sans leading and trailing whitespace
	print '<DD>%s' % string.strip(_prepstring(desc))

    def _write_separator(self, node):
	print '%s<HR>' % self._tab(node)

    def _write_leaf(self, node):
	modified = node.last_modified() or ''
	if modified:
	    modified = ' LAST_MODIFIED="%d"' % modified
	print '%s<DT><A HREF="%s" ADD_DATE="%d" LAST_VISIT="%d"%s>%s</A>' % \
	      (self._tab(node), node.uri(), node.add_date(),
	       node.last_visited(), modified, _prepstring(node.title()))
	self._write_description(node.description())

    def _write_branch(self, node):
	tab = self._tab(node)
	if node.expanded_p(): folded = ''
	else: folded = 'FOLDED '
	print '%s<DT><H3 %sADD_DATE="%d">%s</H3>' % \
	      (tab, folded, node.add_date(), node.title())
	self._write_description(node.description())

    _header = """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
    It will be read and overwritten.
    Do Not Edit! -->
<TITLE>%(title)s</TITLE>
<H1>%(title)s</H1>
<DL><p>"""

    def _write_header(self, root):
	print self._header % {'title': root.title()}

    def _rwrite(self, node):
	tab = '    ' * node.depth()
	if node.isseparator_p(): self._write_separator(node)
	elif node.leaf_p(): self._write_leaf(node)
	else:
	    self._write_branch(node)
	    print '%s<DL><p>' % tab
	    for child in node.children():
		self._rwrite(child)
	    print '%s</DL><p>' % tab

    def write_tree(self, root, fp):
	stdout = sys.stdout
	try:
	    sys.stdout = fp
	    self._write_header(root)
	    for child in root.children():
		self._rwrite(child)
	    print '</DL><p>'
	finally:
	    sys.stdout = stdout
	    fp.close()

class GrailBookmarkWriter(NetscapeBookmarkWriter):
    _header = """<!DOCTYPE GRAIL-Bookmark-file-1>
<!-- This is an automatically generated file.
    It will be read and overwritten.
    Do Not Edit!
    NOTE: This format is fully compatible with
          Netscape 1.x style bookmarks -->
<TITLE>%(title)s</TITLE>
<H1>%(title)s</H1>
<DL><p>"""
