"""Simple extension loader.  Specializations should override the get() method
to do the right thing."""

__version__ = '$Revision: 1.1 $'

import os


class ExtensionLoader:
    def __init__(self, package):
        self.__package = package
        self.__name = package.__name__
        self.__extensions = {}

    def get(self, name):
        ext = self.get_extension(name)
        if ext is None:
            ext = self.find(name)
            if ext is not None:
                self.add_extension(ext)
        return ext

    def find(self, name):
        return self.find_module(name)

    def find_module(self, name):
        realname = "%s.%s" % (self.__name, name)
        d = {}
        try:
            exec ("import %s; mod = %s" % (realname, realname)) in d
        except ImportError:
            mod = None
        else:
            mod = d["mod"]
        return mod

    def add_directory(self, path):
        path = os.path.normpath(os.path.join(os.getcwd(), path))
        if path not in self.__package.__path__:
            self.__package.__path__.insert(0, path)
            return 1
        else:
            return 0

    def add_extension(self, name, extension):
        self.__extensions[name] = extension

    def get_extension(self, name):
        try:
            return self.__extensions[name]
        except KeyError:
            return None
