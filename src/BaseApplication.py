"""Base class for the Grail Application object.

This provides the preferences initialization if needed as well as the
extension loading mechanisms.  The later are the primary motivation
for this, allowing the html2ps.py script to use extensions intelligently
using the same approaches (and implementation) as the Tk-based browser.
"""
__version__ = '$Revision: 2.15 $'
#  $Source: /home/john/Code/grail/src/BaseApplication.py,v $

import keyword
import os
import string

import grailbase.app
import grailbase.mtloader
import grailutil

import sgml.extloader

# make extension packages from these:
import filetypes
import html
import printing.filetypes
import printing.htmltags
import protocols
import protocols.ProtocolAPI


class BaseApplication(grailbase.app.Application):
    def __init__(self, prefs=None):
        grailbase.app.Application.__init__(self, prefs)
        loader = sgml.extloader.TagExtensionLoader(html)
        self.add_loader("html.viewer", loader)
        loader = sgml.extloader.TagExtensionLoader(printing.htmltags)
        self.add_loader("html.postscript", loader)
        loader = grailbase.mtloader.MIMEExtensionLoader(filetypes)
        self.add_loader("filetypes", loader)
        loader = grailbase.mtloader.MIMEExtensionLoader(printing.filetypes)
        self.add_loader("printing.filetypes", loader)
        loader = protocols.ProtocolAPI.ProtocolLoader(protocols)
        self.add_loader("protocols", loader)

        # cache of available extensions
        self.__extensions = {}

    def find_type_extension(self, package, mimetype):
        print "find_type_extension(%s, %s) -->" % (`package`, `mimetype`),
        try:
            loader = self.get_loader(package)
        except KeyError, e:
            print "None"
            return None
        try:
            content_type, opts = grailutil.conv_mimetype(mimetype)
        except:
            print "None"
            return None
        else:
            ext = loader.get(content_type)
            print `ext`
            return ext

    def find_extension(self, subdir, module):
        try:
            return self.get_loader(subdir).get(module)
        except KeyError:
            return None
