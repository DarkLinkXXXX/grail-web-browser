"""Tree walker for visiting the nodes of a bookmarks tree."""

__version__ = '$Revision: 1.4 $'


class TreeWalker:
    def __init__(self, root=None):
        self.__root = root

    def get_root(self):
        return self.__root

    def set_root(self, root):
        if self.__root is not None:
            raise RuntimeError, "cannot change root node"
        self.__root = root

    def walk(self):
        self.__walk(self.get_root())

    def __walk(self, node):
        nodetype = node.get_nodetype()
        try:
            enter_method = getattr(self, "start_" + nodetype)
        except AttributeError:
            pass
        else:
            enter_method(node)
        #
        try:
            children = node.children()
        except AttributeError:
            # doesn't have children()
            pass
        else:
            map(self.__walk, children)
        #
        try:
            leave_method = getattr(self, "end_" + nodetype)
        except AttributeError:
            pass
        else:
            leave_method(node)
