"""Tree nodes used to store the in-memory version of a bookmarks hierarchy."""

import copy
import os
import string
import sys
import time
import urlparse



class Error(Exception):
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)


class AliasReferenceError(Error):
    pass


def norm_uri(uri):
    scheme, netloc, path, params, query, fragment \
            = urlparse.urlparse(uri)
    if scheme == "http" and ':' in netloc:
        loc = string.splitfields(netloc, ':')
        try:
            port = string.atoi(loc[-1], 10)
        except:
            pass
        else:
            if port == 80:
                del loc[-1]
                netloc = string.joinfields(loc, ':')
    return urlparse.urlunparse((scheme, string.lower(netloc), path,
                                params, query, fragment))



class Node:
    def __init__(self):
        pass

    def get_nodetype(self):
        return string.split(self.__class__.__name__, ".")[-1]

    def clone(self):
        return copy.deepcopy(self)

    def leaf_p(self):
        return 1

    def close(self):
        pass


class Alias(Node):
    """Alias for a bookmark node."""

    def __init__(self, ref=None):
        self.__ref = ref
        Node.__init__(self)

    def idref(self):
        return self.__ref.id()

    def get_refnode(self):
        return self.__ref

    def set_refnode(self, ref):
        if self.__ref is not None:
            raise AliasReferenceError("alias already has referent")
        self.__ref = ref


class Separator(Node):
    pass


class DescribableNode(Node):
    """Base class for nodes that can be described with a title and textual
    description.  This also provides support for maintaining information
    about the date the node was added to the bookmarks collection.
    """
    __title = None
    __description = None
    __added = None
    __info = None

    def add_date(self):
        return self.__added

    def title(self):
        return self.__title

    def description(self):
        return self.__description

    def info(self):
        return self.__info


    def set_add_date(self, added):
        self.__added = added

    def set_title(self, title):
        self.__title = title

    def set_description(self, description):
        self.__description = description

    def set_info(self, info):
        self.__info = info


class Bookmark(DescribableNode):
    __id = None
    __uri = None
    __last_modified = None
    __last_response = None
    __last_visited = None


    def id(self):
        return self.__id

    def uri(self):
        return self.__uri

    def last_modified(self):
        return self.__last_modified

    def last_visited(self):
        return self.__last_visited


    def set_id(self, id):
        self.__id = id

    def set_uri(self, uri):
        self.__uri = norm_uri(uri)

    def set_last_modified(self, last_modified):
        self.__last_modified = last_modified

    def set_last_visited(self, last_visited):
        self.__last_visited = last_visited


class Folder(DescribableNode):
    __folded = 0

    def __init__(self):
        self.__children = []
        DescribableNode.__init__(self)

    def children(self):
        return self.__children[:]

    def set_children(self, children):
        self.__children = map(None, children)

    def append_child(self, child):
        self.__children.append(child)

    def insert_child(self, child, index):
        self.__children.insert(index, child)

    def del_child(self, child):
        try:
            i = self.__children.index(node)
            rtnnode = self.__children[i]
            del self.__children[i]
            return rtnnode
        except (ValueError, IndexError):
            return


    def leaf_p(self):
        return 0

    def expand(self):
        self.__folded = 0

    def collapse(self):
        self.__folded = 1

    def expanded_p(self):
        return not self.__folded
