# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:cnri/19980302135001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.4/", or file "LICENSE".

"""Grail parser for text/plain.
"""
__version__ = '$Revision: 2.5 $'
#  $Source: /home/john/Code/grail/src/filetypes/text_plain.py,v $

import formatter
import grailutil
import Reader
import string


def parse_text_plain(*args, **kw):
    headers = args[0].context.get_headers()
    ctype = headers['content-type']
    if ctype:
        ctype, opts = grailutil.conv_mimetype(ctype)
        if opts.get('format'):
            how = string.lower(opts['format'])
            if how == "flowed":
                import FlowingText
                return apply(FlowingText.FlowingTextParser, args, kw)
    return apply(Reader.TextParser, args, kw)
