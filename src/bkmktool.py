#! /usr/bin/env python

# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".

__version__ = '$Revision: 2.2 $'


import os
import sys

grail_root = sys.path[0]
for path in 'utils', 'pythonlib', 'ancillary', 'sgml_lex':
    sys.path.insert(0, os.path.normpath(os.path.join(grail_root, path)))


import bookmarks.main

bookmarks.main.main()
