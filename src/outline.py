"""Framework for managing and displaying outlines
"""

True = 1
False = None



class OutlineNode:
    """The OutlineNode class supports the basics of the tree structure
    implicit in outlines.  The node class manages all pointers within
    the tree.  Non-leaf nodes can be in one of two states: `collapsed'
    (in which the child nodes are recursively hidden), and `expanded'
    (in which the child nodes are visible).

    Methods:

      __init__(data)  -- create an unlinked node containing the data object

      add_child(node) -- append a new child node to the list of children

      del_child(node) -- delete child from list of children.  Return
                         removed node, or None if node was not on list
                         of children.

      replace_child(node, newchild)
                      -- replace the specified child node with the new
                         child node and return the removed node, or
                         None if the node was not on the list of children.

      children()      -- return list of children (None if leaf).  Do
                         not modify this list!

      parent()        -- return the parent node (None if root)

      expand()        -- set node's expand flag

      collapse()      -- reset node's expand flag

      expanded_p()    -- return node's expand flag

      leaf_p()        -- return true if this is a leaf node

      xref()          -- cross reference index into the linear view list

      set_xref(index) -- sets the cross referenced index

      data()          -- returns the node's data object

    Instance Variables:

      No Public Ivars
    """
    gindex = 0

    def __init__(self, data):
	self._leaf_p = True
	self._expanded_p = True
	self._parent = None
	self._children = None
	self._data = None
	self._xref = 0

    def add_child(self, node):
	if self._children is None: self._children = [node]
	else: self._children.append(node)

    def del_child(self, node):
	try:
	    child_i = self._children.index(node)
	    rtnnode = self._children[child_i]
	    del self._children[child_i]
	    if not self._children: self._children = None
	    return rtnnode
	except (ValueError, IndexError):
	    return False

    def replace_child(self, node, newnode):
	try:
	    child_i = self._children.index(node)
	    rtnnode = self._children[child_i]
	    self._children[child_i] = newnode
	    return rtnnode
	except (ValueError, IndexError):
	    return False

    def expand(self): self._expanded_p = True
    def collapse(self): self._expanded_p = False

    def children(self): return self._children
    def parent(self): return self._parent
    def expanded_p(self): return self._expanded_p
    def leaf_p(self): return not not self._children
    def data(self): return self._data

    def xref(self): return self._xref
    def set_xref(self, index): self._xref = index



OutlineIsNonEmpty = 'OutlineIsNonEmpty'
OutlineIsEmpty    = 'OutlineIsEmpty'
LeafNotExpandable = 'LeafNotExpandable'
LeafNotCollapsable = 'LeafNotCollapsable'
InternalError = 'InternalError'


class Outline:
    """Outline class manages the data structures associated with an
    outline.  Specifically, this includes both the expand/collapse
    tree of nodes implicit in the outline, and the flattened list
    structure associated with a linear view of the current state of
    the outline.  Nodes can be added, deleted, expanded, or collapsed
    and both views will remain up-to-date. You can traverse either
    view of the outline by using the interface defined in this class.
    You should not modify the nodes directly.

    Note that in the method descriptions below, when it talks about a
    node being returned, it really means that the data object
    associated with the node is returned.

    Methods:

      __init__()          -- create an empty outline

      root()              -- returns the root of the outline, and sets the
                             `current node pointer' (CNP) to the root.
                             Raises an OutlineIsEmpty exception if
                             there is no root node.

      first_child()       -- sets the CNP to the first child in the node's
                             list of children and returns the node.
                             If the node is a leaf, returns None and
                             leaves the CNP unchanged.

      next_sibling()      -- sets the CNP to the current node's next
                             sibling and returns the node.  If there
                             are no more siblings, this returns None
                             and leaves the CNP unchanged.

      parent()            -- sets the CNP to the current node's parent and
                             returns the node.  If this is the root
                             node, then this returns None and leaves
                             the CNP unchanged.

      next()              -- sets the CNP to the `next' visible node in the
                             linear view of expanded nodes, and
                             returns the node.  Returns None and
                             leaves the CNP unchanged if this is the
                             last node.

      previous()          -- sets the CNP to the `previous' visible node in
                             the linear view of expanded nodes, and
                             returns the node.  Returns None and
                             leaves the CNP unchanged if this is the
                             first node.

      count()             -- return the number of nodes in the linear
                             view.

      goto(index)         -- set the CNP to the node in the linear
                             view indexed by `index'.  Will raise an
                             IndexError if index isn't within 0:count()

      expand()            -- expands the current node by modifying the
                             linear view.  Raises a LeafNotExpandable
                             exception if the current node is a leaf.
                             Returns the number of nodes inserted into
                             the linear view.

      collapse()          -- collapses the current node by modifying the
                             linear view.  Raises a LeafNotCollapsable
                             exception if the current node is a leaf.
                             Returns a tuple of the index of the
                             collapsed node (may be different than the
                             CNP), and the number of nodes removed.
                             See `collapsable_children_p' below.

      set_root(data)      -- set the root node.  If the outline is
                             non-empty, this raises an
                             OutlineIsNonEmpty exception.

      add_child(data)     -- adds a child node (containing the data
                             object) to the current node.  If the node
                             at which the child has been added is
                             expanded, then this Sets the CNP to the
                             new node.

      add_sibling(data)   -- adds a sibling node to the current node.
                             Sets the CNP to the new node.

      insert_parent(data) -- inserts a parent node into the outline.
                             Sets the CNP to the new node

      delete_current()    -- deletes the current node, and
                             recursively, all child nodes.  Sets the
                             CNP to the node's parent.

      excise_current()    -- deletes the current node, but inserts
                             the node's first child into the vacated
                             position in the outline.  Sets the CNP to
                             the inserted node.

      cnp()               -- returns the current node pointer index

    Instance Variables:

      collapsable_children_p  -- when true, collapsing a child node
                                 that is either a leaf, or an already
                                 collapsed branch, actually collapses
                                 the parent node.  By default, this
                                 flag is False
    """
    def __init__(self):
	self._root = None
	self._lview = []
	self._curnode = None
	self._curindex = 0
	self._curparent = None
	self.collapsable_children_p = False

    def _finish(self, node):
	if not node: return False
	self._curnode = node
	self._curparent = self._curnode.parent()
	self._curindex = self._curnode.xref_index()
	return self._curnode.data()

    def root(self):
	if not self._root: raise OutlineIsEmpty
	self._curnode = self._root
	return self._finish()

    def _first_child(self):
	children = self._curnode.children()
	if not children: return False
	return children[0]

    def _next_sibling(self):
	if not self._curparent: return False
	siblings = self._curparent.children()
	# this better be non-empty!
	if not siblings: raise InternalError
	# if this turns out to be too expensive, we could cache this
	# information, but I'm worried that it will be easy to get out
	# of sync, especially given node additions and deletions.
	sib_i = siblings.index(self._curnode) + 1
	# there may be no more siblings
	if sib_i >= siblings.count(): return False
	return siblings[sib_i]

    def _parent(self):
	return self._curparent

    def _goto(self, index):
	# propagate IndexError to caller
	return self._lview[index]

    def _next(self):
	try: return self._lview[self._curindex+1]
	except IndexError: return False

    def _previous(self):
	try: return self._lview[self._curindex-1]
	except IndexError: return False

    def first_child(self): return self._finish(self._first_child())
    def next_sibling(self): return self._finish(self._next_sibling())
    def parent(self): return self._finish(self._parent())
    def goto(self, index): return self._finish(self._goto(index))
    def next(self): return self._finish(self._next())
    def previous(self): return self._finish(self._previous())

    def count(self): return self._lview.count()

    def expand(self):
	if self._curnode.leaf_p(): raise LeafNotExpandable
	if self._curnode.expanded_p(): return 0
	# we need to linearize the nodes to be expanded.  we don't
	# expand recursively so we only need the list of children of
	# the expanded node
	children = self._curnode.children()
	count = children.count()
	#
	if not children: raise InternalError
	self._lview[self._curindex+1:self._curindex+1] = children
	# update the all node's cross reference indexes
	map(lambda node: node.set_xref(node.xref() + count),
	    self._lview[self._curindex+1:])
	# update the node
	self._curnode.expand()
	return count

    def collapse(self):
	start = self._curindex
	# could be an already collapsed leaf
	if not self._curnode.leaf_p() and not self._curnode.expanded_p():
	    return (self._curindex, 0)
	# not a leaf at all, and collapsable_children_p is not set
	if self._curnode.leaf_p() and not self.collapsable_children_p:
	    raise LeafNotCollapsable
	# if it is a leaf and we can still collapse it, we need to
	# recurse up the tree to collapse this node's parent
	if self._curnode.leaf_p():
	    parent = self._curparent
	    if not parent: raise LeafNotCollapsable
	    start = parent.xref()
	# now that we know where to start the collapse, calculate the
	# extent of it.  actually what happens is that we collapse all
	# child nodes under collapse_i.  This means the extent is
	# either from collapse_i to it's next sibling node, or if
	# there is no next sibling, from collapse_i to one of it's
	# ancestor's siblings
	startnode = self._lview[start]
	startparent = startnode.parent()
	thisnode = startnode
	end = None
	while not end:
	    if not startparent:
		end = self._lview.count()
		break
	    sibs = startparent.children()
	    if not sibs:
		startparent = startparent.parent()
	    else:
		nextsib_i = sibs.index(thisnode)
		if nextsib_i+1 < sibs.count():
		    end = sibs[nextsib_i+1].xref()
		else:
		    startparent = startparent.parent()
	# now that we know where to end, lets delete all these nodes
	count = end - start
	del self._lview[start:end]
	# update the xref indices
	map(lambda node: node.set_xref(node.xref() - count),
	    self._lview[end+1:])
	# mark as collapsed
	self._lview[start].collapse()
	return (start, count)

    def set_root(self, data):
	if self._root: raise OutlineIsNonEmpty
	self._root = OutlineNode(data)
	self._lview = [self._root]
	self._curnode = self._root
	self._curnode.set_xref(0)

    def add_child(self, data):
	node = OutlineNode(data)
	self._curnode.add_child(node)
	if self._curnode.expanded_p():
	    self._lview.insert(self._curindex+1, node)
	    map(lambda node: node.set_xref(node.xref() + 1),
		self._lview[self._curindex+1:])
	return self._finish(node)

    def add_sibling(self, data):
	node = OutlineNode(data)
	parent = self._curparent
	# can't add a sibling of root
	if not parent: return False
	children = parent.children()
	lastsib = children[-1]
	index = lastsib.xref()
	# insert into the linear tree.  curnode must be visible and
	# parent must be expanded, otherwise, this wouldn't be the
	# curnode!
	self._lview.insert(index+1, node)
	map(lambda node: node.set_xref(node.xref() + 1),
	    self._lview[index+1])
	return self._finish(node)

    def insert_parent(self, data):
	node = OutlineNode(data)
	parent = self._curparent
	if not parent:
	    # we must be reparenting the root
	    node.add_child(parent)
	    self._root = node
	    map(lambda node: node.set_xref(node.xref() + 1),
		self._lview)
	    self._lview.insert(0, node)
	else:
	    parent.replace_child(self._curnode, node)
	    node.add_child(self._curnode)
	    map(lambda node: node.set_xref(node.xref() + 1),
		self._lview[parent.xref():])
	return self._finish(node)

    def delete_current(self):
	pass

    def excise_current(self):
	pass

    def cnp(self): return self._curindex
