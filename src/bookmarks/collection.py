# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""Bookmark-node manager.

The bookmark node manager supports requesting subsets of the bookmark
collection by URI components.  This is useful for locating a node in the
database which needs to be updated when the user interface successfully
'visits' a node and needs to update the last-visited and last-modified
information.

This class is also used to generate new ID values for nodes.
"""
__version__ = '$Revision: 1.2 $'

import nodes                            # sibling
import search                           # sibling sub-package
import string
import urlparse


class NodeIDError(Exception):
    """Raised when a node with a duplicate ID is added."""
    pass


def _parse_uri(uri):
    """Normalize a URI in parsed form (similar to urlparse() result)."""
    uri = list(urlparse.urlparse(uri))
    if uri[0] == "http":
        host = uri[1]
        if host[-3:] == ":80":
            host = host[:-3]
        uri[1] = string.lower(host)
    else:
        uri[1] = string.lower(uri[1])
    return tuple(uri)


class Collection:
    def __init__(self, root=None):
        self.set_root(root)

    def get_root(self):
        return self.__root

    def set_root(self, root):
        self.__root = root
        if root is not None:
            maps = self.build_info(root)
        else:
            maps = {}, {}, {}
        self.__node_map, self.__id_map, self.__ref_map = maps

    def merge_node(self, node, folder):
        node_map, id_map, ref_map = self.build_info(node)
        d = self.__id_map.copy()
        d.update(id_map)
        if len(d) != (len(id_map) + len(self.__id_map)):
            id_map, ref_map = self.relabel_tree(node, id_map, ref_map)
        self.__id_map.update(id_map)
        self.__ref_map.update(ref_map)
        folder.append_child(node)

    def relabel_tree(self, node, id_map, ref_map):
        """Relabel the IDs of a tree to not conflict with the existing root.
        This should be used to prepare for a merger."""
        need_ids = []
        queue = [node]
        while queue:
            node = queue[0]
            del queue[0]
            nodetype = node.get_nodetype()
            if nodetype in ("Bookmark", "Folder"):
                id = node.id()
                if self.__id_map.has_key(id):
                    # this node must be relabeled:
                    new_id = self.new_id()
                    while id_map.has_key(new_id):
                        new_id = self.new_id()
                    node.set_id(new_id)
                    del id_map[id]
                    id_map[new_id] = node
                    if ref_map.has_key(id):
                        ref_map[new_id] = ref_map[id]
                        del ref_map[id]
        return id_map, ref_map

    __next_id = 1
    __id_format = "bkmk.%s"
    def new_id(self):
        i = self.__next_id
        while 1:
            id = self.__id_format % i
            i = i + 1
            if not self.__id_map.has_key(id):
                break
        self.__next_id = i
        return id

    def build_info(self, node):
        node_map = {}
        id_map = {}
        ref_map = {}
        need_ids = []
        queue = [node]
        while queue:
            node = queue[0]
            del queue[0]
            nodetype = node.get_nodetype()
            if nodetype == "Bookmark":
                id = node.id()
                if id_map.has_key(id):
                    raise NodeIDError("duplicate ID found: " + `id`)
                if id:
                    id_map[id] = node
                    if id in need_ids:
                        need_ids.remove(id)
                uri = node.uri()
                key = urlparse.urlunparse(_parse_uri(uri)[:3] + ('', '', ''))
                try:
                    node_map[key].append(node)
                except KeyError:
                    node_map[key] = [node]
            elif nodetype == "Folder":
                id = node.id()
                if id_map.has_key(id):
                    raise NodeIDError("duplicate ID found: " + `id`)
                if id:
                    id_map[id] = node
                    if id in need_ids:
                        need_ids.remove(id)
                # add child nodes to the end of the queue
                queue[len(queue):] = node.children()
            elif nodetype == "Alias":
                idref = node.idref()
                if not id_map.has_key(idref):
                    need_ids.append(idref)
                try:
                    ref_map[idref].append(node)
                except KeyError:
                    ref_map[idref] = [node]
        if need_ids:
            raise NodeIDError("Could not locate IDs", need_ids)
        return node_map, id_map, ref_map

    def add_Bookmark(self, node):
        self.add_Folder(node)
        key = self.__make_node_key(node)
        try:
            self.__node_map[key].append(node)
        except KeyError:
            self.__node_map[key] = [node]

    def add_Folder(self, node):
        id = node.id()
        if self.__id_map.has_key(id):
            raise NodeIDError("node ID already in ID map")
        if id is not None:
            self.__id_map[id] = node
        

    def del_node(self, node):
        try:
            self.__node_map[self.__make_node_key(node)].remove(node)
        except (KeyError, ValueError, AttributeError):
            pass
        try:
            del self.__id_map[node.id()]
        except (KeyError, AttributeError):
            pass

    def get_node_by_id(self, id):
        try:
            return self.__id_map[id]
        except KeyError:
            return None

    def get_bookmarks_by_uri(self, uri):
        parsed = _parse_uri(uri)
        uri = urlparse.urlunparse(parsed[:3] + ('', '', ''))
        try:
            return tuple(self.__node_map[uri])
        except KeyError:
            return ()

    def __make_node_key(self, node):
        parsed = _parse_uri(node.uri())[:3] + ('', '', '')
        return urlparse.urlunparse(parsed)
