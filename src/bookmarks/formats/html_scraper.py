"""Parser to pull links from an HTML document."""

__version__ = '$Revision: 1.1 $'


import bookmarks.nodes
import SGMLGatherer
import SGMLParser
import string
import urlparse


class Parser(SGMLGatherer.BaseSGMLGatherer):
    __buffer = ''
    __baseurl = None
    __collect_metadata = 0

    from htmlentitydefs import entitydefs

    def __init__(self, filename=None):
        self._filename = filename
        self.sgml_parser = SGMLParser.SGMLParser(gatherer=self)
        self.__root = bookmarks.nodes.Folder()
        self.__root.expand()

    def feed(self, data):
        self.sgml_parser.feed(data)

    def close(self):
        self.sgml_parser.close()

    def save_bgn(self):
        self.__buffer = ''

    __tr = string.maketrans("\r\n\t", "   ")
    def reflow(self, s):
        s = string.translate(s, self.__tr)
        s = string.join(string.split(s))
        return s

    def save_end(self, reflow=1):
        s, self.__buffer = self.__buffer, ''
        if reflow:
            s = self.reflow(s)
        return s

    def handle_data(self, data):
        self.__buffer = self.__buffer + data

    def handle_starttag(self, tag, method, attrs):
        method(self, attrs)

    def get_root(self):
        return self.__root

    # these are probably not useful for subclasses:

    def set_baseurl(self, baseurl):
        self.__baseurl = baseurl

    def start_a(self, attrs):
        uri = string.strip(attrs.get("href", ""))
        if uri:
            self.__node = bookmarks.nodes.Bookmark()
            self.__root.append_child(self.__node)
            if self.__baseurl:
                uri = urlparse.urljoin(self.__baseurl, uri)
            self.__node.set_uri(uri)
            title = self.reflow(attrs.get("title", ""))
            if title:
                self.__node.set_title(title)
        else:
            self.__node = None
        self.save_bgn()

    def end_a(self):
        s = self.save_end()
        if self.__node:
            if not self.__node.title():
                self.__node.set_title(s)
            self.__node = None

    def start_title(self, attrs):
        self.save_bgn()

    def end_title(self):
        s = string.strip(self.save_end())
        if s and not self.__root.title():
            self.__root.set_title(s)

    def start_h1(self, attrs):
        self.start_title({})

    def end_h1(self):
        self.end_title()
