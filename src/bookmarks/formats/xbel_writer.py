"""XBEL writer."""

__version__ = '$Revision: 1.6 $'

import bookmarks
import bookmarks.iso8601
import bookmarks.walker
import string
import sys


class Writer(bookmarks.walker.TreeWalker):
    __depth = 0
    __header = '''\
<!DOCTYPE xbel
  PUBLIC "+//IDN python.org//DTD XML Bookmark Exchange Language 1.0//EN"
         "http://www.python.org/topics/xml/dtds/xbel-1.0.dtd">
'''

    def write_tree(self, fp):
        fp.write(self.__header)
        self.__fp = fp
        self.walk()
        fp.write("</xbel>\n")

    def get_filetype(self):
        return "xbel"

    def start_Folder(self, node):
        info = node.info()
        title = node.title()
        desc = node.description()
        fp = self.__fp
        tab = self.__tab()
        attrs = ''
        added = node.add_date()
        if added:
            attrs = '%s added="%s"' % (attrs, bookmarks.iso8601.ctime(added))
        if node.id():
            attrs = '%s id="%s"' % (attrs, node.id())
        #
        if not self.__depth:
            fp.write("<xbel%s>\n" % attrs)
            if title:
                fp.write("%s  <title>%s</title>\n"
                         % (tab, bookmarks._prepstring(title)))
            if info:
                self.__write_info(info)
            if desc:
                self.__write_description(desc, tab)
            self.__depth = self.__depth + 1
            return
        #
        if node.expanded_p():
            attrs = attrs + ' folded="no"'
        else:
            attrs = attrs + ' folded="yes"'
        if node.children() or title or info or desc:
            fp.write(tab + '<folder%s>\n' % attrs)
            if title:
                fp.write("%s  <title>%s</title>\n"
                         % (tab, bookmarks._prepstring(title)))
            if info:
                self.__write_info(info)
            if desc:
                self.__write_description(desc, tab)
            self.__depth = self.__depth + 1
        else:
            fp.write(tab + '<folder%s/>\n' % attrs)

    def end_Folder(self, node):
        if self.__depth == 1:
            self.__depth = 0
        else:
            if node.children() or node.title():
                self.__fp.write(self.__tab() + "</folder>\n")
            self.__depth = self.__depth - 1

    def start_Separator(self, node):
        self.__fp.write(self.__tab() + "<separator/>\n")

    def start_Alias(self, node):
        idref = node.idref()
        if idref is None:
            sys.stderr.write("Alias node has no referent; dropping.\n")
        else:
            self.__fp.write('%s<alias ref="%s"/>\n'
                            % (self.__tab(), idref))

    def start_Bookmark(self, node):
        date_attr = self.__fmt_date_attr
        added = date_attr(node.add_date(), "added")
        modified = date_attr(node.last_modified(), "modified")
        visited = date_attr(node.last_visited(), "visited")
        desc = string.strip(node.description() or '')
        idref = node.id() or ''
        if idref:
            idref = 'id="%s"' % idref
        info = node.info()
        title = bookmarks._prepstring(node.title() or '')
        uri = bookmarks._prepstring(node.uri() or '')
        attrs = filter(None, (idref, added, modified, visited))
        #
        tab = self.__tab()
        if attrs:
            sep = "\n%s          " % tab
            attrs = " " + string.join(attrs, sep)
        else:
            sep = " "
        self.__fp.write('%s<bookmark%s%shref="%s">\n'
                        % (tab, attrs, sep, uri))
        if title:
            self.__fp.write("%s  <title>%s</title>\n" % (tab, title))
        if info:
            self.__write_info(info)
        if desc:
            self.__write_description(desc, tab)

    def end_Bookmark(self, node):
        self.__fp.write(self.__tab() + "  </bookmark>\n")

    # support methods

    def __write_info(self, info):
        fp = self.__fp
        tab = self.__tab() + "  "
        fp.write(tab + "<info>\n")
        for tag, attrs, content in info:
            fp.write(tab + "  ")
            self.__dump_xml(["metadata", attrs, content], fp, tab + "    ")
            fp.write("\n")
        fp.write(tab + "  </info>\n")

    def __write_description(self, desc, tab):
        w = 60 - len(tab)
        desc = bookmarks._prepstring(desc)
        if len(desc) > w:
            desc = _wrap_lines(desc, 70 - len(tab))
            desc = _indent_lines(desc, len(tab) + 4)
            desc = "\n%s\n%s    " % (desc, tab)
        self.__fp.write("%s  <desc>%s</desc>\n" % (tab, desc))

    def __dump_xml(self, stuff, fp, tab):
        tag, attrs, content = stuff
        has_text = 0
        s = "<" + tag
        space = " "
        for attr, value in attrs.items():
            s = '%s%s%s="%s"' % (s, space, attr, bookmarks._prepstring(value))
            space = "\n%s%s" % (tab, " "*len(tag))
        fp.write(s)
        if not content:
            fp.write("/>")
            return
        has_text = (tab is None) or (attrs.get("xml:space") == "preserve")
        if not has_text:
            for citem in content:
                if type(citem) is type(""):
                    has_text = 1
                    break
        if has_text:
            # some plain text in the data; assume significant:
            fp.write(">")
            for citem in content:
                if type(citem) is type(""):
                    fp.write(bookmarks._prepstring(citem))
                else:
                    # element
                    self.__dump_xml(citem, fp, None)
        else:
            fp.write(">\n")
            for citem in content:
                fp.write(tab)
                self.__dump_xml(citem, fp, tab + "  ")
                fp.write("\n")
            fp.write(tab)
        fp.write("</%s>" % tag)

    def __fmt_date_attr(self, date, attrname):
        if date:
            return '%s="%s"' % (attrname, bookmarks.iso8601.ctime(date))
        return ''

    def __tab(self):
        return "  " * self.__depth


def _wrap_lines(s, width):
    words = string.split(s)
    lines = []
    buffer = ''
    for w in words:
        if buffer:
            nbuffer = "%s %s" % (buffer, w)
            if len(nbuffer) > width:
                lines.append(buffer)
                buffer = w
            else:
                buffer = nbuffer
        else:
            buffer = w
    if buffer:
        lines.append(buffer)
    return string.join(lines, "\n")


def _indent_lines(s, indentation):
    lines = string.split(s, "\n")
    tab = " " * indentation
    return tab + string.join(lines, "\n" + tab)
