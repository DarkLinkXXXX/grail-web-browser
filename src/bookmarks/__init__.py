# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:cnri/19980302135001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.4/", or file "LICENSE".

import os
import string
import sys
import urlparse


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


class BookmarkReader:
    def __init__(self, parser):
        self.__parser = parser

    def read_file(self, fp):
        self.__parser.feed(fp.read())
        self.__parser.close()
        return self.__parser.get_root()


class BookmarkWriter:
    # base class -- subclasses are required to set _filetype attribute
    def get_filetype(self):
        return self._filetype


__tr_map = {}
for c in map(chr, range(256)):
    __tr_map[c] = c
for c in "<>&'\"":
    __tr_map[c] = "&#%d;" % ord(c)

def _prepstring(s):
    """Return HTML/XML safe copy of a string."""
    return string.join(map(__tr_map.get, s), '')



# The canonical table of supported bookmark formats:
__formats = {
    # format-name     first-line-magic
    #                  short-name   extension
    "html":          ('<!DOCTYPE\s+(GRAIL|NETSCAPE)-Bookmark-file-1',
                      "html",      ".html"),
    "pickle":        ('#.*GRAIL-Bookmark-file-2',
                      "pickle",    ""),
    "pickle-binary": ('#.*GRAIL-Bookmark-file-3',
                      "bpickle",   ""),
    "xbel":          ('<(\?xml|!DOCTYPE)\s+xbel',
                      "xbel",      ".xml"),
    }

__format_inited = 0

def __init_format_table():
    global __format_inited
    global __format_table
    import re
    __format_table = table = []
    for result, (rx, sname, ext) in __formats.items():
        if rx:
            rx = re.compile(rx)
            table.append((rx, result))
    __format_inited = 1

def get_format(fp):
    if not __format_inited:
        __init_format_table()
    format = None
    pos = fp.tell()
    try:
        line1 = fp.readline()
        for re, fmt in __format_table:
            if re.match(line1):
                format = fmt
    finally:
        fp.seek(pos)
    return format


def get_short_name(format):
    return __formats[format][1]

def get_default_extension(format):
    return __formats[format][2]


def get_parser_class(format):
    exec "from formats.%s_parser import Parser" % get_short_name(format)
    return Parser

def get_writer_class(format):
    sname = get_short_name(format)
    exec "from formats.%s_writer import Writer" % sname
    return Writer


def get_handlers(format, filename):
    parser_class = get_parser_class(format)
    writer_class = get_writer_class(format)
    parser = writer = None
    if parser_class is not None:
        parser = parser_class(filename)
    if writer_class is not None:
        writer = writer_class()
    return parser, writer
