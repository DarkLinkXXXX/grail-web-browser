"""<OBJECT> handler for Python applets."""

__version__ = '$Revision: 1.4 $'

import grailutil
import string

import AppletLoader
import HTMLParser


def embed_text_x_python(parser, attrs):
    """<OBJECT> Handler for Python applets."""
    extract = grailutil.extract_keyword
    width = extract('width', attrs, conv=string.atoi)
    height = extract('height', attrs, conv=string.atoi)
    menu = extract('menu', attrs, conv=string.strip)
    classid = extract('classid', attrs, conv=string.strip)
    codebase = extract('codebase', attrs, conv=string.strip)
    align = extract('align', attrs, 'baseline')
    vspace = extract('vspace', attrs, 0, conv=string.atoi)
    hspace = extract('hspace', attrs, 0, conv=string.atoi)
    apploader = AppletLoader.AppletLoader(
        parser, width=width, height=height, menu=menu,
        classid=classid, codebase=codebase,
        vspace=vspace, hspace=hspace, align=align, reload=parser.reload1)
    if apploader.feasible():
        return AppletEmbedding(apploader)
    else:
        apploader.close()
    return None


class AppletEmbedding(HTMLParser.Embedding):
    """Applet interface for use with <OBJECT> / <PARAM> elements."""

    def __init__(self, apploader):
        self.__apploader = apploader

    def param(self, name, value):
        self.__apploader.set_param(name, value)

    def end(self):
        self.__apploader.go_for_it()
