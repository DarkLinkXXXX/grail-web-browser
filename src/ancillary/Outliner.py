import string

True = 1
False = None


class OutlineNode:
    def __init__(self):
	self._expanded_p = True
	self._parent = None
	self._children = []
	self._depth = 0

    def __repr__(self):
	if self.leaf_p(): tag = '|'
	elif self.expanded_p(): tag = '-'
	else: tag = '+'
	return tag + ('_' * (self._depth * 3))

    def append_child(self, node):
	self._children.append(node)
	node._parent = self
	node._depth = self._depth + 1

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
