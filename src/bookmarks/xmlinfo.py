#! /usr/bin/env python
#  -*- python -*-

"""Support for retrieving useful information about XML data, including the
public and system IDs and the document type name."""

__version__ = "$Revision: 1.1 $"

import copy
import os
import re
import string
import struct
import sys

BOM_BE = "\xfe\xff"
BOM_LE = "\xff\xfe"

BIG_ENDIAN = "big-endian"
LITTLE_ENDIAN = "little-endian"

if struct.pack('h', 1) == struct.pack('>h', 1):
    NATIVE_ENDIANNESS = BIG_ENDIAN
else:
    NATIVE_ENDIANNESS = LITTLE_ENDIAN


class Error(Exception):
    """Base class for xmlinfo exceptions."""
    pass

class ConversionError(Error):
    """Raised when an encoding conversion fails."""
    pass

class ParseError(Error):
    pass

class EncodingMismatchError(ParseError):
    """Raised when an extractor thinks it's reading from a stream of the
    wrong encoding.  The exception parameter is the name of a suggested
    encoding to try, or None.
    """
    def __init__(self, encoding=None):
        self.encoding = encoding
        ParseError.__init__(self, encoding)


class Record:
    public_id = None
    system_id = None
    doc_elem = None
    standalone = None
    xml_version = None
    encoding = None
    byte_order = None

    def __init__(self, **kw):
        self.__dict__.update(kw)


def get_xml_info(buffer):
    values = Record(standalone="no", xml_version="1.0")
    # determine byte-order and encoding:
    bom = get_byte_order_mark(buffer)
    buffer = buffer[len(bom):]
    if bom == BOM_BE:
        values.byte_order = BIG_ENDIAN
        values.encoding = "utf-16"
    elif bom == BOM_LE:
        values.byte_order = LITTLE_ENDIAN
        values.encoding = "utf-16"
    elif bom == '':
        byte_order, encoding = guess_byte_order_and_encoding(buffer)
        values.byte_order = byte_order
        values.encoding = encoding
    else:
        raise RuntimeError, \
              "unexpected internal condition: bad byte-order mark"
    # parse the XML encoding declaration:
    return extract(values.encoding, buffer, values)


def get_byte_order_mark(buffer):
    bom = buffer[:2]
    if bom in (BOM_BE, BOM_LE):
        return bom
    else:
        return ''


def guess_byte_order_and_encoding(buffer):
    """This can be used to guess the byte-order and encoding when no BOM
    is present."""
    byte_order = None
    encoding = "utf-8"
    #
    prefix = buffer[:4]
    if prefix == "\0\0\0\x3c":
        byte_order = BIG_ENDIAN
        encoding = "ucs-4"
    elif prefix == "\x3c\0\0\0":
        byte_order = LITTLE_ENDIAN
        encoding = "ucs-4"
    elif prefix == "\0\x3c\0\x3f":
        byte_order = BIG_ENDIAN
        encoding = "utf-16"
    elif prefix == "\x3c\0\x3f\0":
        byte_order = LITTLE_ENDIAN
        encoding = "utf-16"
    elif prefix == "\x3c\x3f\x78\x6d":
        # good enough to parse the encoding declaration
        encoding = "utf-8"
    elif prefix == "\x4c\x4f\xa7\x94":
        encoding = "ebcdic"
    #
    return byte_order, encoding


def extract(encoding, buffer, values):
    tried = {}
    while not tried.has_key(encoding):
        tried[encoding] = 1
        v2 = copy.copy(values)
        extractor = new_extractor(encoding, buffer, v2)
        try:
            v2 = extractor.extract()
        except EncodingMismatchError, e:
            encoding = e.encoding
        else:
            return v2
    raise ParseError("could not determine encoding")


_extractor_map = {}
def new_extractor(encoding, buffer, values):
    encoding = string.lower(encoding)
    klass = _extractor_map.get(encoding, Extractor)
    return klass(buffer, values)


class Extractor:
    __VERSION_CHARS = string.letters + string.digits + "_.:-"

    encoding = None

    def __init__(self, buffer, values):
        self.buffer = buffer
        self.values = values

    def extract(self):
        self.parse_declaration()
        if self.values.encoding != self.encoding:
            raise EncodingMismatchError(self.values.encoding)
        self.skip_to_doctype()
        self.parse_doctype()
        return self.values

    def parse_declaration(self):
        try:
            self.require_ascii("<?xml", "XML declation")
        except ParseError:
            # OK to drop this for UTF-8
            return
        self.parse_VersionInfo()
        attrname, encoding = self.get_opt_pseudo_attr()
        if attrname == "encoding":
            self.values.encoding = string.lower(encoding)
            attrname, standalone = self.get_opt_pseudo_attr()
            if attrname == "standalone":
                if standalone not in ("yes", "no"):
                    raise ParseError(
                        "illegal standalone value in XML declaration: "
                         + value)
                self.values.standalone = standalone
                attrname = None
        if attrname is not None:
            raise ParseError(
                "unknown or out-of-order XML declaration attribute: "
                + attrname)
        self.skip_whitespace()
        self.require_ascii("?>", "XML declaration")

    def parse_VersionInfo(self):
        attr, verno = self.get_pseudo_attr()
        if attr != 'version':
            raise ParseError(
               "first pseudo-attribute in XML declaration must be version")
        if not verno:
            raise ParseError("version number cannot be empty")
        for c in verno:
            if not c in self.__VERSION_CHARS:
                raise ParseError(
                    "illegal character in XML version declaration: " + `c`)
        self.values.xml_version = verno

    def get_pseudo_attr(self):
        """Return attr/value pair using the XML declaration's idea of a
        pseudo-attribute."""
        attrname = ''
        value = ''
        self.require_whitespace("pseudo-attribute")
        while 1:
            c = self.get_ascii(1)
            if c in string.letters:
                attrname = attrname + c
                self.discard_chars(1)
            else:
                break
        if not attrname:
            raise ParseError("could not extract pseudo-attribute name")
        self.skip_whitespace()
        self.require_ascii("=", "pseudo-attribute")
        self.skip_whitespace()
        open_quote = self.get_ascii(1)
        if open_quote not in ('"', "'"):
            raise ParseError("pseudo-attribute values must be quoted")
        self.discard_chars(1)
        while 1:
            c = self.get_ascii(1)
            if not c:
                raise ParseError("could not complete pseudo-attribute value")
            self.discard_chars(1)
            if c == open_quote:
                break
            value = value + c
        return attrname, value

    def get_opt_pseudo_attr(self):
        buffer = self.buffer
        try:
            return self.get_pseudo_attr()
        except ParseError:
            self.buffer = buffer
            return None, None

    def parse_doctype(self):
        raise NotImplementedError

    def skip_comment(self):
        raise NotImplementedError

    def skip_pi(self):
        raise NotImplementedError

    def skip_to_doctype(self):
        raise NotImplementedError

    def skip_whitespace(self):
        """Trim leading whitespace, returning the number of characters
        stripped."""
        raise NotImplementedError

    def require_whitespace(self, where):
        """Trim leading whitespace, returning the number of characters
        stripped or raising ParseError is no whitespace was present."""
        numchars = self.skip_whitespace()
        if not numchars:
            raise ParseError("required whitespace in " + where)

    def require_ascii(self, str, where):
        data = self.get_ascii(len(str))
        if data != str:
            raise ParseError("required text '%s' missing in %s" % (str, where))
        self.discard_chars(len(str))

    def discard_chars(self, count):
        raise NotImplementedError


class ISO8859Extractor(Extractor):
    __declattr_rx = re.compile(
        "([a-z]*)=\"((?:[^?\"]|\?[^?>\"]|\?(?=\?))*)\"", re.MULTILINE)

    __gi_rx = re.compile("[a-zA-Z_:][-a-zA-Z_:0-9.]*")
    __id_rx = re.compile(r"""(?:'[^']*'|\"[^\"]*\")""",
                         re.MULTILINE | re.VERBOSE)

    def __yank_id(self):
        self.require_whitespace("doctype declaration")
        m = self.__id_rx.match(self.buffer)
        if not m:
            return None
        self.buffer = self.buffer[m.end():]
        return string.lstrip(m.group())[1:-1]

    def parse_doctype(self):
        self.require_ascii("<!DOCTYPE", "doctype declaration")
        self.require_whitespace("doctype declaration")
        m = self.__gi_rx.match(self.buffer)
        if not m:
            raise ParseError("could not parse doctype declaration: no name")
        self.values.doc_elem = m.group()
        self.discard_chars(len(self.values.doc_elem))
        whitechars = self.skip_whitespace()
        if not self.buffer:
            raise ParseError("could not parse doctype declaration:"
                             " insufficient data")
        if self.get_ascii(1) in ">[":
            # reached internal subset or end of declaration; we're done
            return
        if not whitechars:
            raise ParseError("whitespace required between document type and"
                             " document type declaration")
        str = self.get_ascii(6)
        if str == "PUBLIC":
            # public system id w/ optional system id
            self.discard_chars(len(str))
            id = self.__yank_id()
            if not id:
                raise ParseError("could not parse doctype declaration:"
                                 " bad public id")
            self.values.public_id = id
            self.values.system_id = self.__yank_id()

        elif str == "SYSTEM":
            #  system id
            self.discard_chars(len(str))
            id = self.__yank_id()
            if not id:
                raise ParseError("could not parse doctype declaration:"
                                 " bad system id")
            self.values.system_id = id

    def skip_to_doctype(self):
        while self.buffer:
            self.buffer = string.lstrip(self.buffer)
            if self.buffer[:4] == "<!--":
                self.skip_comment()
            elif self.buffer[:2] == "<?":
                self.skip_pi()
            else:
                break

    def skip_pi(self):
        pos = string.find(self.buffer, "?>", 2)
        if pos < 0:
            raise ParseError("could not scan over processing instruction")
        self.buffer = self.buffer[pos + 2:]

    def skip_comment(self):
        pos = string.find(self.buffer, "-->", 4)
        if pos < 0:
            raise ParseError("could not scan over comment")
        self.buffer = self.buffer[pos + 4:]

    def skip_whitespace(self):
        old_buffer = self.buffer
        self.buffer = string.lstrip(old_buffer)
        return len(old_buffer) - len(self.buffer)

    def get_ascii(self, count):
        # not quite right, but good enough for now
        return self.buffer[:count]

    def discard_chars(self, count):
        self.buffer = self.buffer[count:]


for c in "123456789":
    class _Extractor(ISO8859Extractor):
        encoding = "iso-8859-" + c
    try:
        _Extractor.__name__ = "ISO8859_%s_Extractor" % c
    except TypeError:
        # older Python versions wouldn't allow __name__ to be set on a class
        pass
    exec "ISO8859_%s_Extractor = _Extractor" % c
    _extractor_map["iso-8859-" + c] = _Extractor


class UTF8Extractor(ISO8859Extractor):
    encoding = "utf-8"

_extractor_map["utf-8"] = UTF8Extractor


def ascii_to_ucs2be(s):
    L = map(None, s)
    L.insert(0, '')
    return string.join(L, '\0')


def ascii_to_ucs2le(s):
    L = map(None, s)
    L.append('')
    return string.join(L, '\0')


class UCS2Extractor(Extractor):
    __WHITESPACE_BE = map(ascii_to_ucs2be, string.whitespace)
    __WHITESPACE_LE = map(ascii_to_ucs2le, string.whitespace)

    def __init__(self, buffer, values):
        Extractor.__init__(self, buffer, values)
        if values.byte_order not in (BIG_ENDIAN, LITTLE_ENDIAN):
            raise ValueError, \
                  "UCS-2 encoded strings must have determinable byte order"
        self.__byte_order = values.byte_order
        if values.byte_order == BIG_ENDIAN:
            self.__whitespace = self.__WHITESPACE_BE
            self.__from_ascii = ascii_to_ucs2be
        else:
            self.__whitespace = self.__WHITESPACE_LE
            self.__from_ascii = ascii_to_ucs2le

    def parse_declaration(self):
        prefix = self.__from_ascii("<?xml")
        if self.buffer[:len(prefix)] != prefix:
            raise ParseError("could not parse XML declaration")
        self.buffer = self.buffer[len(prefix):]
        self.parse_VersionInfo()

    def skip_whitespace(self):
        buffer = self.buffer
        count = 0
        while buffer[:2] in self.__whitespace:
            buffer = buffer[2:]
            count = count + 1
        self.buffer = buffer
        return count

    def get_ascii(self, count):
        data = self.buffer[:count*2]
        if self.__byte_order == BIG_ENDIAN:
            zero_offset = 0
            char_offset = 1
        else:
            zero_offset = 1
            char_offset = 0
        s = ''
        try:
            for i in range(0, count, 2):
                if data[i+zero_offset] != '\0':
                    raise ConversionError("cannot convert %s to ASCII"
                                          % `data[i:i+2]`)
                s = s + data[i+char_offset]
        except IndexError:
            # just didn't have enough; somebody else's problem
            pass
        return s

    def discard_chars(self, count):
        self.buffer = self.buffer[count*2:]


def ordwc(wc, byte_order=None):
    """Return the ord() for a wide character."""
    if byte_order is None:
        byte_order = NATIVE_ENDIANNESS
    width = len(wc)
    if width == 2:
        o1, o2 = map(ord, wc)
        if byte_order == BIG_ENDIAN:
            ord = (o1 << 8) | o2
        else:
            ord = (o2 << 8) | o1
    elif width == 4:
        o1, o2, o3, o4 = map(ord, wc)
        if byte_order == BIG_ENDIAN:
            ord = (((((o1 << 8) | o2) << 8) | o3) << 8) | o4
        else:
            ord = (((((o4 << 8) | o3) << 8) | o2) << 8) | o1
    else:
        raise ValueError, "wide-character string has bad length"
    return ord


def ordwstr(wstr, byte_order=None, charsize=2):
    assert charsize in (2, 4), "wide character size must be 2 or 4"
    ords = []
    for i in range(0, len(wstr), charsize):
        ords.append(ordwc(wstr[i:i+charsize], byte_order))
    return ords


def main():
    import getopt
    #
    reqs = Record()                     # required values (for output)
    #
    get_defaults = 1
    full_report = 0
    opts, args = getopt.getopt(sys.argv[1:], "a",
                               ["all", "docelem", "encoding", "public",
                                "standalone", "system", "version"])
    if opts:
        get_defaults = 0
    for opt, arg in opts:
        if opt in ("-a", "--all"):
            full_report = 1
        elif opt == "--docelem":
            reqs.doc_elem = 1
        elif opt == "--encoding":
            reqs.encoding = 1
        elif opt == "--public":
            reqs.publib_id = 1
        elif opt == "--standalone":
            reqs.standalone = 1
        elif opt == "--system":
            reqs.system_id = 1
        elif opt == "--version":
            reqs.xml_version = 1
    if get_defaults:
        full_report = 1
    #
    if len(args) > 1:
        sys.stderr.write("%s: too many input sources specified"
                         % os.path.basename(sys.argv[0]))
        sys.exit(2)
    if args:
        if os.path.exists(args[0]):
            fp = open(args[0])
        else:
            import urllib
            fp = urllib.urlopen(args[0])
    else:
        fp = sys.stdin
    #
    values = get_xml_info(fp.read(10240))
    #
    # Make the report:
    #
    field_names = dir(Record)
    field_names.remove("__doc__")
    field_names.remove("__init__")
    field_names.remove("__module__")
    if full_report:
        labels = Record(
            system_id="System ID",
            public_id="Public ID",
            doc_elem="Document Element",
            standalone="Standalone",
            xml_version="XML Version",
            encoding="Encoding",
            byte_order="Byte Order",
            )
        format = "%%%ds: %%s" % max(map(len, labels.__dict__.values()))
        for field_name in field_names:
            value = getattr(values, field_name)
            label = getattr(labels, field_name)
            if value is not None:
                print format % (label, value)
    else:
        for field_name in field_names:
            if getattr(reqs, field_name):
                value = getattr(values, field_name)
                if value is None:
                    print
                else:
                    print value


if __name__ == "__main__":
    main()
