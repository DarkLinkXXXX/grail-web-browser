# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""Base class for the Grail Application object.

This provides the preferences initialization if needed as well as the
extension loading mechanisms.  The later are the primary motivation
for this, allowing the html2ps.py script to use extensions intelligently
using the same approaches (and implementation) as the Tk-based browser.
"""
__version__ = '$Revision: 2.13 $'
#  $Source: /home/john/Code/grail/src/BaseApplication.py,v $

import keyword
import mimetypes
import os
import posixpath
import regsub
import string
import sys

import grailutil
import GrailPrefs

DEFAULT_DEVICE = 'viewer'               # should be 'writer', but this support
                                        # legacy HTML extensions


# downgrade the keyword module for 1.4 & older if needed:
try:
    exec "assert 1"
except SyntaxError:
    if "assert" in keyword.kwlist:
        keyword.kwlist.remove("assert")
        del keyword.kwdict["assert"]
    if not "access" in keyword.kwlist:
        keyword.kwlist.insert(0, "access")
        keyword.kwdict["access"] = 1


class BaseApplication:
    def __init__(self, prefs=None):
        grailutil._grail_app = self
        self.prefs = prefs or GrailPrefs.AllPreferences()
        self.graildir = grailutil.getgraildir()
        self.iconpath = [os.path.join(grailutil.get_grailroot(), 'icons')]
        self.get_package("html")        # make it a 'user' package
        grailutil.establish_dir(self.graildir)
        user_icons = os.path.join(self.graildir, 'icons')
        if os.path.isdir(user_icons):
            self.iconpath.insert(0, user_icons)
        # cache of available extensions
        self.__extensions = {}
        #
        # Add our type map file to the set used to initialize the shared map:
        #
        typefile = os.path.join(self.graildir, "mime.types") 
        mimetypes.init(mimetypes.knownfiles + [typefile])

    # Mapping '.' to os.sep to test for the user dir is needed to support
    # nested packages.
    __pkg2path_map = string.maketrans('.', os.sep)
    def get_package(self, name):
        exec "import %s; package = %s" % (name, name)
        userdir = os.path.join(self.graildir,
                               string.translate(name, self.__pkg2path_map))
        if os.path.isdir(userdir) and userdir not in package.__path__:
            package.__path__.insert(0, userdir)
        return package

    def get_package_module(self, pkgname, modname):
        package = self.get_package(pkgname) # make it a 'user' package
        if not package:
            return None
        if keyword.iskeyword(modname):
            modname = modname + "_"
        pkgname = package.__name__
        exec "from %s import %s; mod = %s" % (pkgname, modname, modname)
        return mod

    def find_embedder(self, devicetype, mimetype):
        modname, mod = self.find_type_extension("obj_" + devicetype, mimetype)
        if modname:
            name = "embed_" + modname
            if hasattr(mod, name):
                return getattr(mod, name)
        return None

    def find_type_extension(self, package, mimetype):
        try:
            content_type, opts = grailutil.conv_mimetype(mimetype)
        except:
            return None, None
        [type, subtype] = string.splitfields(content_type, '/')
        type = regsub.gsub("[^a-zA-Z0-9_]", "_", type)
        subtype = regsub.gsub("[^a-zA-Z0-9_]", "_", subtype)
        result = None, None
        for modname in (type + "_" + subtype, type):
            mod = self.find_extension(package, modname)
            if mod:
                return modname, mod
        return None, None

    __tagmask = string.maketrans('-.', '__')
    def find_html_extension(self, tag, device):
        tag = string.translate(tag, self.__tagmask)
        if not self.__have_taginfo(tag, device):
            mod = self.find_extension("html", tag)
            if mod:
                self.load_tag_handlers(mod)
        if self.__have_taginfo(tag, device):
            return self.__get_taginfo(tag, device)
        return None

    def load_tag_handlers(self, mod):
        as_list = 1
        if hasattr(mod, "ATTRIBUTES_AS_KEYWORDS"):
            as_list = not mod.ATTRIBUTES_AS_KEYWORDS
        handlers = {}
        for name in dir(mod):
            parts = string.splitfields(name, "_")
            if len(parts) not in (2, 3):
                continue
            if not (parts[-2] and parts[-1] and parts[0]):
                continue
            if len(parts) == 2:
                device = DEFAULT_DEVICE
                [action, tag] = parts
            else:
                [device, action, tag] = parts
            start = do = end = None
            if handlers.has_key((tag, device)):
                start, do, end = handlers[(tag, device)]
            if action == 'start':
                start = getattr(mod, name)
                if as_list:
                    start = ListAttributesCaller(start)
            elif action == 'end':
                end = getattr(mod, name)
            elif action == 'do':
                do = getattr(mod, name)
                if as_list:
                    do = ListAttributesCaller(do)
            handlers[(tag, device)] = (start, do, end)
        from sgml.SGMLParser import TagInfo
        for (tag, device), (start, do, end) in handlers.items():
            if start or do:
                taginfo = TagInfo(tag, start, do, end)
                self.__taginfo[(tag, device)] = taginfo

    __taginfo = {}
    def __get_taginfo(self, tag, device):
        return self.__taginfo[(tag, device)]

    def __have_taginfo(self, tag, device):
        return self.__taginfo.has_key((tag, device))

    def find_extension(self, subdir, module):
        key = (subdir, module)
        if self.__extensions.has_key(key):
            return self.__extensions[key]
        mod = None
        try:
            mod = self.get_package_module(subdir, module)
        except ImportError:
            pass
        except:
            self.exception_dialog("while importing %s.%s" % (subdir, module))
        self.__extensions[key] = mod
        return mod

    #######################################################################
    #
    #  Misc. support.
    #
    #######################################################################

    def exception_dialog(self, message="", *args):
        raise RuntimeError, "Subclass failed to implement exception_dialog()."

    import regex
    __data_scheme_re = regex.compile(
        "data:\([^,;]*\)\(;\([^,]*\)\|\),", regex.casefold)
    def guess_type(self, url):
        """Guess the type of a file based on its URL.

        Return value is a string of the form type/subtype, usable for
        a MIME Content-type header; or None if no type can be guessed.

        """
        if self.__data_scheme_re.match(url) >= 0:
            scheme = self.__data_scheme_re.group(1) or "text/plain"
            return string.lower(scheme), self.__data_scheme_re.group(3)
        return mimetypes.guess_type(url)


def _nullfunc(*args, **kw):
    pass


class ListAttributesCaller:
    """Call a tag handler function, translating the attributes dictionary to
    a list.

    This is useful for legacy HTML tag extensions.  The SGML & HTML support
    in Grail never has to see attributes as lists; simplifying and supporting
    a number of automatic value normalizations (esp. URI normalization and ID/
    IDREF support).
    """
    def __init__(self, func):
        self.__func = func

    def __call__(self, parser, attrs):
        return apply(self.__func, (parser, attrs.items()))
