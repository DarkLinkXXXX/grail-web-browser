"""Writer for Grail's pickled bookmarks."""

__version__ = '$Revision: 1.1 $'


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

    def set_original_filename(self, filename):
        self.__filename = filename

    def set_original_mtime(self, mtime):
        self.__mtime = mtime

    def write_tree(self, root, fp):
        try:
            fp.write(self.HEADER_STRING)
            fp.write(self.__filename + "\n")
            fp.write(`self.__mtime` + "\n")
            pickle.dump(root, fp, 1)
        finally:
            fp.close()
