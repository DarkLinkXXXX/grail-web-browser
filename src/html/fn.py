# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".

"""Footnote support for Grail.

This supports the <FN ID=name> form of the footnote tag.
"""

__version__ = '$Revision: 2.8 $'


ATTRIBUTES_AS_KEYWORDS = 1

from grailutil import extract_keyword


def writer_start_fn(parser, attrs):
    if 'p' in parser.stack:
        parser.lex_endtag('p')
        parser.formatter.end_paragraph(0)
    else:
        parser.formatter.add_line_break()


def writer_end_fn(parser):
    parser.formatter.pop_style()
