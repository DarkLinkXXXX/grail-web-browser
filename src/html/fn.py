"""Footnote support for Grail.

This supports the <FN ID=name> form of the footnote tag.
"""
__version__ = '$Revision: 2.2 $'
#  $Source: /home/john/Code/grail/src/html/fn.py,v $


ATTRIBUTES_AS_KEYWORDS = 1

from grailutil import extract_keyword


def start_fn(parser, attrs):
    if 'p' in parser.stack:
	parser.lex_endtag('p')
	parser.formatter.end_paragraph(0)
    else:
	parser.formatter.add_line_break()
    name = extract_keyword('id', attrs)
    parser.formatter.push_style(name and '#' + name or None)


def end_fn(parser):
    parser.formatter.pop_style()


#
#  end of file
