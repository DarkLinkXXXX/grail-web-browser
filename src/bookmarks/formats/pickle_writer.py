# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""Writer for Grail's pickled bookmarks."""

__version__ = '$Revision: 1.3 $'


import bookmarks                        # parent

try:
    import cPickle
except ImportError:
    import pickle
else:
    pickle = cPickle


class Writer(bookmarks.BookmarkWriter):
    HEADER_STRING = "# GRAIL-Bookmark-file-4 (cache pickle format)\n"
    _filetype = "pickle"

    __filename = ""
    __mtime = 0

    def __init__(self, root):
        self.__root = root

    def set_original_filename(self, filename):
        self.__filename = filename

    def set_original_mtime(self, mtime):
        self.__mtime = mtime

    def write_tree(self, fp):
        try:
            fp.write(self.HEADER_STRING)
            fp.write(self.__filename + "\n")
            fp.write(`self.__mtime` + "\n")
            pickle.dump(self.__root, fp, 1)
        finally:
            fp.close()
