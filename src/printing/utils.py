# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".

"""Small utility functions for printing support, mostly for debugging."""

__version__ = '$Revision: 1.3 $'

import sys


def find_word_breaks(data):
    datalen = nextbrk = len(data)
    prevbreaks = [-1] * datalen
    nextbreaks = [datalen] * datalen
    indexes = range(datalen)
    #
    prevbrk = -1
    for i in indexes:
        prevbreaks[i] = prevbrk
        if data[i] == ' ':
            prevbrk = i
    #
    indexes.reverse()
    for i in indexes:
        nextbreaks[i] = nextbrk
        if data[i] == ' ':
            nextbrk = i
    #
    return prevbreaks, nextbreaks


_subsystems = {}

def debug(text, subsystem=None):
    if get_debugging(subsystem):
        if text[-1] <> '\n':
            text = text + '\n'
        sys.stderr.write(text)
        sys.stderr.flush()


def set_debugging(flag, subsystem=None):
    if not _subsystems.has_key(subsystem):
        _subsystems[subsystem] = 0
    _subsystems[subsystem] = max(
        _subsystems[subsystem] + (flag and 1 or -1), 0)


def get_debugging(subsystem=None):
    if _subsystems.has_key(subsystem):
        return _subsystems[subsystem]
    if subsystem:
        return get_debugging()
    return 0


# unit conversions:
def inch_to_pt(inches): return inches * 72.0
def pt_to_inch(points): return points / 72.0


def distance(start, end):
    """Returns the distance between two points."""
    if start < 0 and end < 0:
        return abs(min(start, end) - max(start, end))
    elif start >= 0 and end >= 0:
        return max(start, end) - min(start, end)
    else:
        #  one neg, one pos
        return max(start, end) - min(start, end)


def image_loader(url):
    """Simple image loader for the PrintingHTMLParser instance."""
    #
    # This needs a lot of work for efficiency and connectivity
    # with the rest of Grail, but works O.K. if there aren't many images
    # or if blocking can be tolerated.
    #
    # Some sites don't handle this very well, including www.microsoft.com,
    # which returns HTTP 406 errors when html2ps is used as a script
    # (406 = "No acceptable objects were found").
    #
    from urllib import urlopen
    try:
        imgfp = urlopen(url)
    except IOError, msg:
        return None
    return imgfp.read()
