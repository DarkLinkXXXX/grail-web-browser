"""Attribute handling and value conversion functions.

This module is safe for 'from sgml.utils import *'.

"""
__version__ = '$Revision: 1.2 $'


import string
_string = string
del string


def extract_attribute(key, dict, default=None, conv=None, delete=1):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function, and
    DELETE (if true) says to delete the extracted key from the
    dictionary upon successful extraction.

    """
    if dict.has_key(key):
        val = dict[key]
        if delete:
            del dict[key]
        if not conv:
            return val
        try:
            return conv(val)
        except:
            return default
    return default


def extract_keyword(key, dict, default=None, conv=None):
    """Extracts an attribute from a dictionary.

    KEY is the attribute name to look up in DICT.  If KEY is missing
    or cannot be converted, then DEFAULT is returned, otherwise the
    converted value is returned.  CONV is the conversion function.
    """
    if dict.has_key(key):
        if conv:
            try:
                return conv(dict[key])
            except:
                return default
        return dict[key]
    return default


def conv_integer(val, conv=_string.atoi, otherlegal=''):
    val = _string.strip(val)
    l = len(val)
    start = 0
    if val[0] in '+-':
        start = 1
    legalchars = _string.digits + otherlegal
    for i in range(start, l):
        if val[i] not in legalchars:
            val = val[:i]
            break
    return conv(val)


def conv_float(val):
    return conv_integer(val, conv=_string.atof, otherlegal='.')


def conv_normstring(val):
    return _string.lower(_string.strip(val))


def conv_enumeration(val, mapping_or_list):
    val = conv_normstring(val)
    if type(mapping_or_list) == type([]):
        if val in mapping_or_list: return val
        else: return None
    else:
        if mapping_or_list.has_key(val): return mapping_or_list[val]
        else: return None


def conv_normwhitespace(val):
    return _string.join(_string.split(val))


def conv_exists(val):
    return 1


def conv_mimetype(type):
    """Convert MIME media type specifications to tuples of
    ('type/subtype', {'option': 'value'}).
    """
    if not type:
        return None, {}
    if ';' in type:
        i = _string.index(type, ';')
        opts = _parse_mimetypeoptions(type[i + 1:])
        type = type[:i]
    else:
        opts = {}
    fields = _string.split(_string.lower(type), '/')
    if len(fields) != 2:
        raise ValueError, "Illegal media type specification."
    type = _string.join(fields, '/')
    return type, opts


def _parse_mimetypeoptions(options):
    opts = {}
    options = _string.strip(options)
    while options:
        if '=' in options:
            pos = _string.find(options, '=')
            name = _string.lower(_string.strip(options[:pos]))
            value = _string.strip(options[pos + 1:])
            options = ''
            if ';' in value:
                pos = _string.find(value, ';')
                options = _string.strip(value[pos + 1:])
                value = _string.strip(value[:pos])
            if name:
                opts[name] = value
        else:
            options = None
    return opts