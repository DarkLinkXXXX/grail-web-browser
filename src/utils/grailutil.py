"""Miscellaneous utilities for Grail."""

__version__ = "$Revision: 2.24 $"

import os

# TBD: hack!  grail.py calculates grail_root, which would be
# convenient to export to extensions, but you can't `import grail' or
# `import __main__'.  grail.py isn't designed for that.  You could
# `from grail import grail_root' but that's kind of gross.  This
# global holds the value of grail_root which can be had with
# grailutil.get_grailroot()
_grail_root = None
_grail_app = None

# XXX Unix specific stuff
# XXX (Actually it limps along just fine for Macintosh, too)

def getgraildir():
    return getenv("GRAILDIR") or os.path.join(gethome(), ".grail")

def get_grailroot():
    return _grail_root

def get_grailapp():
    return _grail_app

def gethome():
    try:
        home = getenv("HOME")
        if not home:
            import pwd
            user = getenv("USER") or getenv("LOGNAME")
            if not user:
                pwent = pwd.getpwuid(os.getuid())
            else:
                pwent = pwd.getpwnam(user)
            home = pwent[6]
        return home
    except (KeyError, ImportError):
        return os.curdir

def getenv(s):
    if os.environ.has_key(s): return os.environ[s]
    return None

def which(filename, searchlist=None):
    if searchlist is None:
        import sys
        searchlist = sys.path
    for dir in searchlist:
        found = os.path.join(dir, filename)
        if os.path.exists(found):
            return found
    return None

def establish_dir(dir):
    """Ensure existence of DIR, creating it if necessary.

    Returns 1 if successful, 0 otherwise."""
    if os.path.isdir(dir):
        return 1
    head, tail = os.path.split(dir)
    if not establish_dir(head):
        return 0
    try:
        os.mkdir(dir, 0777)
        return 1
    except os.error:
        return 0

def complete_url(url):
    import urlparse
    scheme, netloc = urlparse.urlparse(url)[:2]
    if not scheme:
        if not netloc:
            # XXX url2pathname/pathname2url???
            if os.path.exists(url):
                import urllib
                url = "file:" + urllib.quote(url)
            else:
                url = "http://" + url
        else:
            url = "http:" + url
    return url

def nicebytes(n):
    """Convert a bytecount to a string like '<number> bytes' or '<number>K'.

    This is intended for inclusion in status messages that display
    things like '<number>% read of <bytecount>' or '<bytecount> read'.
    When the byte count is large, it will be expressed as a small
    floating point number followed by K, M or G, e.g. '3.14K'.

    The word 'bytes' (or singular 'byte') is part of the returned
    string if the byte count is small; when the count is expressed in
    K, M or G, 'bytes' is implied.

    """
    if n < 1000:
        if n == 1: return "1 byte"
        return "%d bytes" % n
    n = n * 0.001
    if n < 1000.0:
        suffix = "K"
    else:
        n = n * 0.001
        if n < 1000.0:
            suffix = "M"
        else:
            n = n * 0.001
            suffix = "G"
    if n < 10.0: r = 2
    elif n < 100.0: r = 1
    else: r = 0
    return "%.*f" % (r, n) + suffix



import string

# HTML utilities.  This should maybe go someplace else, but it should
# definitely be a function and not a method of some class.

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

def conv_integer(val, conv=string.atoi, otherlegal=''):
    val = string.strip(val)
    l = len(val)
    start = 0
    if val[0] in '+-':
        start = 1
    legalchars = string.digits + otherlegal
    for i in range(start, l):
        if val[i] not in legalchars:
            val = val[:i]
            break
    return conv(val)

def conv_float(val):
    return conv_integer(val, conv=string.atof, otherlegal='.')

def conv_normstring(val):
    return string.lower(string.strip(val))

def conv_enumeration(val, mapping_or_list):
    val = conv_normstring(val)
    if type(mapping_or_list) == type([]):
        if val in mapping_or_list: return val
        else: return None
    else:
        if mapping_or_list.has_key(val): return mapping_or_list[val]
        else: return None

def conv_normwhitespace(val):
    return string.join(string.split(val))

def conv_exists(val):
    return 1


def conv_fontsize(spec):
    """Parse a font size with an optional leading specification.

    spec
        should be a string representing a real number or a pair of real
        numbers separated by a forward slash.  Whitespace is ignored.

    This function returns a tuple of the fontsize and leading.  If the
    leading is not specified by `spec', the leading will be the same as
    the font size.

    """
    if '/' in spec:
        spec = string.splitfields(spec, '/')
        if len(spec) != 2:
            raise ValueError, "illegal font size specification"
    else:
        spec = [spec, spec]
    spec = map(string.atof, map(string.strip, spec))
    return tuple(spec)


def conv_mimetype(type):
    """Convert MIME media type specifications to tuples of
    ('type/subtype', {'option': 'value'}).
    """
    if not type:
        return None, {}
    if ';' in type:
        i = string.index(type, ';')
        opts = _parse_mimetypeoptions(type[i + 1:])
        type = type[:i]
    else:
        opts = {}
    fields = string.splitfields(string.lower(type), '/')
    if len(fields) != 2:
        raise ValueError, "Illegal media type specification."
    type = string.joinfields(fields, '/')
    return type, opts


def _parse_mimetypeoptions(options):
    opts = {}
    options = string.strip(options)
    while options:
        if '=' in options:
            pos = string.find(options, '=')
            name = string.lower(string.strip(options[:pos]))
            value = string.strip(options[pos + 1:])
            options = ''
            if ';' in value:
                pos = string.find(value, ';')
                options = string.strip(value[pos + 1:])
                value = string.strip(value[:pos])
            if name:
                opts[name] = value
        else:
            options = None
    return opts


def pref_or_getenv(name, group='proxies', type_name='string',
                   check_ok=None, user=0, factory=0):
    """Help for integrating environment variables with preferences.

    First check preferences, under 'group', for the component 'name'.
    If 'name' is defined as a 'string' and it's NULL, try to read
    'name' from the environment.  If 'name's defined in the
    environment, migrate the value to preferences.  Return the value
    associated with the name, None if it's not defined in either place
    (env or prefs... and it's a 'string').  If check_ok is not None,
    it is expected to be a tuple of valid names. e.g. ('name1',
    'name2').  If factory is TRUE then the value for name is retrieved
    only from factory defaults and not user preferences and not the
    environment. If it's not found there, return None.

    """
    if check_ok and  name not in check_ok:
            return None

    app = get_grailapp()

    if type_name == 'string':
        component = app.prefs.Get(group, name, factory=factory)
        if len(component) or factory:
            return component
    elif type_name == 'int':
        component = app.prefs.GetInt(group, name, factory=factory)
        return component
    elif type_name == 'Boolean':
        component = app.prefs.GetBoolean(group, name, factory=factory)
        return component
    elif type_name == 'float':
        component = app.prefs.GetFloat(group, name, factory=factory)
        return component
    else:
        raise ValueError, ('%s not supported - must be one of %s'
                      % (`type_name`, ['string', 'int', 'float', 'Boolean']))

    import os
    try:
        component = os.environ[name]
    except:
        return None

    app.prefs.Set(group, name, component)
    return component

