import string

True = 1
False = None


class OutlinerNode:
    def __init__(self):
	self._expanded_p = True
	self._parent = None
	self._children = []
	self._depth = 0
	self._index = None

    def __repr__(self):
	tabdepth = self._depth - 1
	if self.leaf_p(): tag = ' '
	elif self.expanded_p(): tag = '+'
	else: tag = '-'
	return (' ' * (tabdepth * 3)) + tag

    def close(self):
	self._parent = None
	for child in self._children: child.close()

    def _redepthify(self, node):
	depth = node.depth()
	for child in node.children():
	    child._depth = depth + 1
	    self._redepthify(child)

    def append_child(self, node):
	self._children.append(node)
	node._parent = self
	node._depth = self._depth + 1
	self._redepthify(node)

    def insert_child(self, node, index):
	self._children.insert(index, node)
	node._parent = self
	node._depth = self._depth + 1
	self._redepthify(node)

    def del_child(self, node):
	try:
	    child_i = self._children.index(node)
	    rtnnode = self._children[child_i]
	    del self._children[child_i]
	    return rtnnode
	except (ValueError, IndexError):
	    return False

    def replace_child(self, node, newnode):
	newnode._depth = self._depth + 1
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
    def leaf_p(self): return not self._children

    def depth(self): return self._depth
    def index(self): return self._index
    def set_index(self, index): self._index = index



class OutlinerViewer:
    _gcounter = 0

    def __init__(self, root):
	self._root = root
	self._nodes = []
	self._gcounter = 0
	self._follow_all_children_p = False

    def __del__(self): self._root.close()

    def _insert(self, node, index=None):
	"""Derived class specialization"""
	pass

    def _delete(self, start, end=None):
	"""Derived class specialization"""
	pass

    def _populate(self, node):
	# insert into linear list
	self._nodes.append(node)
	node.set_index(self._gcounter)
	self._gcounter = self._gcounter + 1
	# calculate the string to insert into the list box
	self._insert(node)
	if self._follow_all_children_p or node.expanded_p():
	    for child in node.children():
		self._populate(child)

    def populate(self):
	self._populate(self._root)

    def insert_nodes(self, at_index, node_list, before_p=False):
	if not before_p: at_index = at_index + 1
	nodecount = len(node_list)
	for node in node_list:
	    self._nodes.insert(at_index, node)
	    self._insert(node, at_index)
	    node.set_index(at_index)
	    at_index = at_index + 1
	for node in self._nodes[at_index:]:
	    node.set_index(node.index() + nodecount)

    def delete_nodes(self, start, end):
	nodecount = end - start + 1
	self._delete(start, end)
	for node in self._nodes[end+1:]:
	    node.set_index(node.index() - nodecount)
	del self._nodes[start:end+1]

    def update_node(self, node):
	index = node.index()
	# TBD: is there a more efficient way of doing this!
	self._delete(index)
	self._insert(node, index)

    def _expand(self, node):
	for child in node.children():
	    self.insert_nodes(self._gcounter, [child], True)
	    self._gcounter = self._gcounter + 1
	    if not child.leaf_p() and child.expanded_p():
		self._expand(child)

    def expand_node(self, node):
	self._gcounter = node.index() + 1
	self._expand(node)

    def node(self, index):
	if 0 <= index < len(self._nodes): return self._nodes[index]
	else: return None

    def count(self): return len(self._nodes)
