"""Handle Management System client library.

This module implements the low-level client library for the Handle
Management System from CNRI.  For more information, see
http://WWW.CNRI.Reston.VA.US/home/cstr/handle-intro.html

CNRI has made available a C library that implements the protocol,
however that is not used here for a number of reasons:

  1. The C library has not yet been built as a shared library, so
     including handle resolution in Grail using the C library would
     require a re-link of the python binary.

  2. We can experiment more easily with a fully Python protocol
     implementation.

  3. It's more fun to hack Python than C!

On the downside, this module must remain in sync with the current HMS
protocol.  The module currently (as of 31-Aug-1995) implements an
older version of the protocol.  With the imminent release of a version
supporting local handle systems, this module will have to be
rewritten.  The LHS changes complicate matters considerably, but we
will still attempt to implement it in Python.

Update 24-Oct-1995: I am rewriting this to conform to the new handle
client library protocol.

Classes:

- Error -- exception for error conditions specific to this module 
- HashTable -- hash table class

XXX Should break up get_data in send_request and poll_request
XXX When retrying, should we generate a new tag or reuse the old one?
XXX When an incomplete result is returned, should we raise an exception?
XXX Should we cache the hash table entries read from the file?

"""

import rand
import md5
import os
import select
import socket
import string
import time
import xdrlib

DEBUG = 0				# Default debugging flag


HASH_TABLE_FILE_FALLBACK = 'hdl_hash_tbl'

internal_consts = """
CONFIG_FILE = '/etc/handle.conf'
DEFAULT_SERVER = 'hs.cnri.reston.va.us'
DEFAULT_HASH_FILE = '/etc/hdl_hash_tbl'
FILE_NAME_LENGTH = 128
HOST_NAME_LENGTH = 64
MAX_BODY_LENGTH = 1024
UDP = 0
TCP = 1
PROTOCOL = 1
NO_CONFIG = -1
CONFIG = -2
FIRST_SCAN_OF_CONFIG = -3
SUCCESS = 1
FAILURE = -1
"""

# Put internal_constants mappings into the module's dictionary, and
# into the data_map dictionary.  Also create an inverted mapping.
exec internal_consts
consts_map = {}
exec internal_consts in consts_map
for key, value in consts_map.items():
    if key != '__builtins__':
	consts_map[value] = key



# Useful constants
MAGIC = ".HASH_TABLE"			# Hash table file magic number


# The following stuff is from handle.h and handle_protocol.h
HDL_NONMUTABLE = 0			# LSB (0th bit)
HDL_DISABLED = 1			# (1st bit)
flags_map = {0: 'HDL_NONMUTABLE', 1: 'HDL_DISABLED'}

# Handle protocol miscellaneous constants
HP_VERSION = 0				# Handle protocol version
HP_NAME = "hdl-srv"			# Service name
HP_PORT = 2222				# Used if service "hdl-srv" is unknown

# Handle protocol lengths
HP_HEADER_LENGTH = 28			# Packet header length
HP_MAX_COMMAND_SIZE = 512		# Max command packet length
HP_MAX_DATA_VALUE_LENGTH = 128
HP_MD5_CHECKSUM_BYTE_LENGTH = 16

# Handle protocol commands (packet types)
HP_QUERY = 0
HP_QUERY_RESPONSE = 1



# Handle data types
data_types = """
HDL_TYPE_NULL = -1			# Indicates End of Type List
HDL_TYPE_URL = 0			# Uniform Resource Locator
HDL_TYPE_EMAIL_RFC822 = 1		# E-Mail Address Defined In RFC822
HDL_TYPE_EMAIL_X400 = 2			# E-Mail Address Defined By CCITT
HDL_TYPE_X500_DN = 3			# Distinguished Name Defined By CCITT
HDL_TYPE_INET_HOST = 4			# Internet Host Name Or IP Address
HDL_TYPE_INET_SERVICE = 5		# "hostname":"tcp"|"udp":"port"
HDL_TYPE_CONTACT_INFO = 6		# Same Syntax As EMAIL_RFC822
HDL_TYPE_DLS = 7			# TBD
HDL_TYPE_CACHE_PERIOD = 8		# default caching period
HDL_TYPE_HANDLE_TYPE = 9		# For HDM Internal Use
"""

# Put data_types mappings into the module's dictionary, and into the
# data_map dictionary.  Also create an inverted mapping.
exec data_types
data_map = {}
exec data_types in data_map
for key, value in data_map.items():
    if key != '__builtins__':
	data_map[value] = key



# Handle protocol error codes
error_codes = """
HP_OK = 0
HDL_ERR_OK = 0
HDL_ERR_INVALID = -1
HDL_ERR_TIMEOUT = -2
HDL_ERR_REDIRECTED = -3
HDL_ERR_NO_SUCH_SERVER = -4
HDL_ERR_INVALID_FLAG = -5
HDL_ERR_PROTOCOL = -6
HDL_ERR_INTERNAL_ERROR = -7
HDL_ERR_VERSION = -8
HDL_ERR_PARSING_FAILURE = -9
HDL_ERR_ACCESS_DENIED = -10
HDL_ERR_SERVER_NOT_RESP = -11
HDL_ERR_NOT_FOUND = -12
HDL_ERR_USAGE = -13
HDL_ERR_SESSION_TAG_MISMATCH = -14
HDL_ERR_TYPES_NOT_FOUND = -15
HDL_ERR_SERVER_ERROR = -16
HDL_ERR_HASH_TBL_FILE_NOT_FOUND = -17
HDL_ERR_HASH_TBL_FILE_CORRUPTED = -18
HDL_ERR_HASH_TBL_ENTRY_NOT_FOUND = -19
HDL_ERR_DOES_NOT_EXIST = -20
"""

# See data_types comment above
exec error_codes
error_map = {}
exec error_codes in error_map
for key, value in error_map.items():
    if key != '__builtins__':
	error_map[value] = key




# error class for this module
class Error:
    """Exception class for module hdllib."""
    def __init__(self, msg=None):
	self.msg = msg
    def __repr__(self):
	return repr(self.msg)
    def __str__(self):
	return str(self.msg)



class PacketPacker(xdrlib.Packer):
    """Helper class to pack packets."""

    def pack_header(self, tag=0, command=HP_QUERY, err=0, sequence=1,
		   total=1, version=HP_VERSION):
	"""Pack the packet header (except the body length).

	The argument order differs from the order in the
	packet header so we can use defaults for most fields.

	"""

	self.pack_uint(version)
	self.pack_uint(tag)
	self.pack_uint(command)
	self.pack_uint(sequence)
	self.pack_uint(total)
	self.pack_int(err)

    def pack_body(self, hdl, flags = [], types = [], replyport = 0,
		  replyaddr = '\0\0\0\0'):
	"""Pack the packet body (preceded by its length)."""

	# Build the body first, so we can include its length
	# in the header
	p = xdrlib.Packer()
	p.pack_string(hdl)
	p.pack_uint(len(flags))
	for flag in flags:
	    p.pack_uint(flag)
	    p.pack_opaque(chr(1))
	p.pack_uint(len(types))
	for type in types:
	    p.pack_uint(type)
	p.pack_uint(replyport)
	p.pack_opaque(replyaddr)

	body = p.get_buf()

	self.pack_uint(len(body))

	self.buf = self.buf + body



class PacketUnpacker(xdrlib.Unpacker):
    """Helper class to unpack packets."""

    def unpack_header(self):
	"""Unpack a packet header (except the body length).

	The argument order corresponds to the arguments to
	packheader().

	"""

	version = self.unpack_uint()
	tag = self.unpack_uint()
	command = self.unpack_uint()
	sequence = self.unpack_uint()
	total = self.unpack_uint()
	err = self.unpack_int()

	return (tag, command, err, sequence, total, version)

    def check_body_length(self):
	"""Check that the body length matches what the header says.

	If it doesn't, raise Error.

	"""
	length = self.unpack_uint()
	if len(self.buf) - self.pos != length:
	    print "length according to header:",
	    print length,
	    print "actual length:",
	    print len(self.buf) - self.pos
	    raise Error("body length mismatch")

    def unpack_item_array(self):
	"""Unpack an array of (type, value) pairs."""
	nopts = self.unpack_uint()
	opts = []
	for i in range(nopts):
	    opt = self.unpack_uint()
	    val = self.unpack_opaque()
	    opts.append((opt, val))
	return opts

    def unpack_request_body(self):
	"""Unpack a request body (preceded by its length)."""

	self.check_body_length()

	hdl = self.unpack_string()

	options = self.unpack_item_array()

	ntypes = self.unpack_uint()
	types = []
	for i in range(ntypes):
	    types.append(self.unpack_uint())

	replyport = self.unpack_uint()
	replyaddr = self.unpack_opaque()

	return (hdl, options, types, replyport, replyaddr)

    def unpack_reply_body(self):
	"""Unpack a reply body (preceded by its length).

	Make sure the checksum is correct, else raise Error.

	"""

	self.check_body_length()

	start = self.pos

	flags = self.unpack_opaque()

	items = self.unpack_item_array()

	checksum = self.unpack_fopaque(16)
	digest = md5.new(self.buf[start:-16]).digest()
	if digest != checksum:
	    raise Error("body checksum mismatch")

	return flags, items

    def unpack_error_body(self, err):
	"""Unpack an error reply body according to the error code."""

	# XXX Should save the error code in self.unpack_header()?

	self.check_body_length()

	if err == HP_VERSION_MISMATCH:
	    return self.unpack_uint()
	elif err == HP_HANDLE_NOT_FOUND:
	    return None
	elif err in (HP_NOT_RESPONSIBLE_FOR_HANDLE,
		       HP_FORWARDED,
		       HP_ACCESS_TEMPORARILY_DENIED,
		       HP_PARSING_FAILURE):
	    return self.unpack_string()
	else:
	    return `self.buf[self.pos:]`



class SessionTag:
    """Session tag.  See client library equivalent in
    create_tag.c: create_session_tag().

    Methods:

    session_tag() -- get next session tag
    """
    def session_tag(self):
	"""Implemented as in create_session_tag()."""
	now = time.time()
	try: seed = now % os.getpid()
	except: seed = now
	rand.srand(int(seed))
	return rand.rand()



class HSConfig:
    """Handle client configuration file parser.
    See hdl_client_config.c:process_config()

    Methods:

        __init__(FILE)  -- parses the configuration file

    Ivars:

        status       -- NO_CONFIG or CONFIG (whether a config file was found)
        protocol     -- TCP or UDP
        server_name  -- handle server name to connect to
        udp_port     -- port number for udp
        tcp_port     -- port number for tcp
        hash_path    -- path in filesystem to hash table
    """
    def __init__(self, filename=CONFIG_FILE):
	# set up defaults
	self.status = FIRST_SCAN_OF_CONFIG
	self.protocol = UDP
	self.server_name = ''
	self.udp_port = -1
	self.tcp_port = -1
	self.hash_path = DEFAULT_HASH_FILE

	required_keywords = {
	    'clientprotocol': 'ClientProtocol',
	      'udpqueryport': 'UDPQueryPort',
	      'tcpqueryport': 'TCPQueryPort',
	        'servername': 'ServerName'
	    }
	
	# crack the config file
	try: fp = open(filename, 'r')
	except IOError:
	    self.status = NO_CONFIG
	    return

	lines = fp.readlines()
	fp.close()
	linenum = 0
	for line in lines:
	    linenum = linenum + 1
	    tokens = string.split(line)
	    # skip comments and blank lines
	    if not tokens or tokens[0] == '#': continue
	    # switch on token
	    keyword = string.lower(tokens[0])
	    if keyword == 'clientprotocol':
		ptype = string.lower(tokens[1])
		if ptype == 'tcp': self.protocol = TCP
		elif ptype == 'udp': self.protocol = UDP
		else:
		    # TBD: should go to stderr
		    print 'Syntax error in', filename, 'file'
		    print 'ClientProtocol must be either TCP or UDP, line:', \
			  linenum
		    self.status = HDL_ERR_INTERNAL_ERROR
		    return
		    
	    elif keyword == 'udpqueryport':
		self.udp_port = string.atoi(tokens[1])
	    elif keyword == 'tcpqueryport':
		self.tcp_port = string.atoi(tokens[1])
	    elif keyword == 'hashpath':
		self.hash_path = tokens[1]
	    elif keyword == 'servername':
		self.server_name = tokens[1]
	    else:
		# TBD: should go to standard error
		print 'Syntax error in', filename, 'file'
		print 'Invalid keyword found:', keyword, ' on line:', linenum
		self.status = HDL_ERR_INTERNAL_ERROR
		return
	    del required_keywords[keyword]

	# verify that all non-optional keywords were found
	if required_keywords:
	    # TBD: should go to stderr
	    print 'Syntax error in', filename, 'file'
	    print 'The following non-optional parameters were not defined:'
	    for rk in required_keywords.values(): print rk,
	    print
	    self.status = HDL_ERR_INTERNAL_ERROR
	    return

	self.status = CONFIG
	


class HashTable:
    """Handle server hash table.

    This class basically implements the algorithm described in the
    client library method get_hash.c:hdl_get_service_ptr().

    Methods:

    __init__(FILE, DEBUG) -- loads the hash table
    set_debuglevel(DEBUG) -- set the debug level
    """
    def __init__(self, filename=None, debug=None):
	if debug is None: debug = DEBUG
	self.debug = debug

	# see if the hash table already exists
	if not filename:
	    if os.path.exists(DEFAULT_HASH_FILE):
		filename = DEFAULT_HASH_FILE
	    else:
		filename = HASH_TABLE_FILE_FALLBACK
	try:
	    if self.debug: print "Opening hash table:", `self.filename`
	    fp = open(self.filename, 'rb')
	except IOError:
	    # hash table does not already exist so we need to send a
	    # request for the hash table
	    if self.debug: print "Requesting hash table"
	    
	    


#class HandleCache:
#    """Cache of handle resolution attempts.
#
#    This class caches both hits and misses, in order to properly
#    support relative handle URNs.  Here's the current semantics.
#
#    Let's say you resolve a handle such as hdl://cnri-1/cnri_home
#    where `cnri-1' is the naming authority.  This resolves to the URL
#    http://www.cnri.reston.va.us/.  This page contains some relative
#    URLs.  Without forcing the author to register every single handle
#    in her set of digital objects, we propose allowing only the root
#    object to be register, and allowing this to refer to the entire
#    set of objects.
#
#    Thus if within this page, a link to a relative URL is found such
#    as /home/cstr/handle-intro.html then the resolution scheme occurs
#    as follows:
#
#    hdl://cnri-1/home/cstr/handle-intro.html (if that fails...)
#    hdl://cnri-1/home/cstr                   (if that fails...)
#    hdl://cnri-1/home                        (if that fails...)
#    hdl://cnri-1/


class HashTable:
    """Hash table.

    Methods:

    - __init__(FILE) -- constructor
    - set_debuglevel(DEBUG) -- set debug level
    - hash_handle(HANDLE) -- hash a handle to handle server info
    - get_data(hdl, types, flags, timeout) -- resolve a handle

    """	
    def __init__(self, filename = None, debug = None):
	"""Hash table constructor.

	Read the hash table file header from optional FILE and
	hold on to the open file.  Store the header fields as
	instance variables.  Optional DEBUG sets debugging
	level.

	Exceptions:

	- Error
	- IOError
	- whatever xdrlib raises

	"""

	self.tag = SessionTag()

	if not filename:
	    if os.path.exists(DEFAULT_HASH_FILE):
		filename = DEFAULT_HASH_FILE
	    else:
		filename = HASH_TABLE_FILE_FALLBACK
	if debug is None: debug = DEBUG

	self.filename = filename
	self.debug = debug

	self.bucket_cache = {}

	if self.debug: print "Opening hash table:", `self.filename`
	try:
	    self.fp = fp = open(self.filename, 'rb')
	except IOError:
	    if self.debug: print "Using hardcoded fallback scheme"
	    self.nbits = 0
	    self.bucket_cache[0] = ("hs.cnri.reston.va.us",
				    2222,
				    210,
				    "dely@cnri.reston.va.us")
	else:
	    if fp.read(len(MAGIC)) != MAGIC:
		raise Error("Hash table magic word error")

	    u = xdrlib.Unpacker(fp.read(16))
	    self.length = u.unpack_int()
	    self.version = u.unpack_int()
	    self.nbits = u.unpack_int()
	    self.maxbucket = u.unpack_int()

	    if self.debug:
		print '*'*20
		print "Hash table file header:"
		print "length:        ", self.length
		print "version:       ", self.version
		print "nbits:         ", self.nbits
		print "maxbucket:     ", self.maxbucket
		print '*'*20

	    # XXX Should do some sanity checks here


    def set_debuglevel(self, debug):
	"""Set the debug level to LEVEL."""
	self.debug = debug


    def hash_handle(self, hdl):
	"""Hash a HANDLE to a tuple of handle server info.

	Return (ip-address, query-port, admin-port, mailbox).

	A leading "//" is stripped from the handle and it is
	converted to upper case before taking its MD-5 digest.
	The first 'nbits' bits of the digest are then used to
	compute the hash table bucket index; the selected
	bucket is read from the hash table file and decoded.

	Exceptions may be raised by xdrlib if the entry is
	corrupt.

	"""

	# XXX Should do some sanity checks here

	if self.nbits > 0:
	    if hdl[:2] == '//': hdl = hdl[2:]
	    hdl = string.upper(hdl)
	    digest = md5.new(hdl).digest()
	    u = xdrlib.Unpacker(digest)
	    index = u.unpack_uint()
	    index = index >> (32 - self.nbits)
	else:
	    index = 0

	if self.bucket_cache.has_key(index):
	    return self.bucket_cache[index]

	pos = self.length + (index * self.maxbucket)
	self.fp.seek(pos)

	entry = self.fp.read(self.maxbucket)
	u = xdrlib.Unpacker(entry)

	ipaddr = u.unpack_opaque()
	qport = u.unpack_int()
	aport = u.unpack_int()
	mailbox = u.unpack_string()

	ipaddr = string.joinfields(map(repr, map(ord, ipaddr)), '.')

	result = (ipaddr, qport, aport, mailbox)
	self.bucket_cache[index] = result

	return result


    def get_data(self, hdl, types=[], flags=[], timeout=30, interval=5):
	"""Get data for HANDLE of the handle server.

	Optional arguments are a list of desired TYPES, a list
	of FLAGS, and a maximum TIMEOUT in seconds (default
	30 seconds).

	Exceptions:

	- Error
	- socket.error
	- whatever xdrlib raises

	"""

	mytag = self.tag.session_tag()

	p = PacketPacker()
	p.pack_header(mytag)
	p.pack_body(hdl, flags, types)
	request = p.get_buf()

	(server, qport, aport, mailbox) = self.hash_handle(hdl)

	if self.debug:
	    # XXX Perhaps this should be in hash_handle()?
	    print "="*20
	    print "Hash bucket info:"
	    print "server: ", `server`
	    print "qport:  ", `qport`
	    print "aport:  ", `aport`
	    print "mailbox:", `mailbox`
	    print "="*20

	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	if self.debug: print "Send request"
	s.sendto(request, (server, qport))

	expected = 1
	responses = {}
	endtime = time.time() + timeout

	while len(responses) != expected:

	    t = time.time()
	    if t > endtime:
		raise Error("timed out")
		break

	    (readers, writers, extras) = select.select(
		    [s], [], [], min(endtime-t, interval))

	    if s not in readers:
		if self.debug: print "Nothing received yet..."
		t = time.time()
		if t+interval < endtime:
		    if self.debug: print "Resend request"
		    s.sendto(request, (server, qport))
		continue

	    reply, fromaddr = s.recvfrom(1024)
	    u = PacketUnpacker(reply)
	    (tag, command, err, sequence, total, version) = \
		  u.unpack_header()

	    if self.debug:
		print '-'*20
		print "Reply header:"
		print "Version:       ", version
		print "Session tag:   ", tag
		print "Command:       ", command
		print "Sequence#:     ", sequence
		print "#Datagrams:    ", total
		print "Error code:    ", err,
		if error_map.has_key(err):
		    print "(%s)" % error_map[err],
		print
		print '-'*20

	    if tag != mytag:
		if self.debug: print "bad session tag"
		continue

	    if command != HP_QUERY_RESPONSE:
		if self.debug: print "bad reply type"
		continue

	    if not 1 <= sequence <= total:
		if self.debug: print "bad sequence number"
		continue

	    expected = total

	    if err != HP_OK:
		error_body = u.unpack_error_body(err)
		if self.debug:
		    print "Error body:", error_body
		raise Error((err, error_body))

	    flags, items = u.unpack_reply_body()

	    responses[sequence] = (flags, items)

	s.close()

	allflags = None
	allitems = []
	for i in range(1, expected+1):
	    if responses.has_key(i):
		(flags, items) = responses[i]
		allflags = flags
		allitems = allitems + items
	return (allflags, allitems)



# Test sets

testsets = [
	# 0: Official demo handle (with and without //)
	[
	"//cnri-1/cnri_home",
	"cnri-1/cnri_home",
	],
	# 1: Some demo handles I added
	[
	"nonreg.guido/python-home-web-site",
	"nonreg.guido/python-home-page",
	"nonreg.guido/python-home-ftp-dir",
	"nonreg.guido/python-ftp-dir",
	],
	# 2: Test various error conditions
	[
	"nonreg.bad.domain/irrelevant",
	"nonreg.guido/non-existing",
	"nonreg.guido/invalid-\1",
	"",
	"nonreg.guido",
	"nonreg.guido/",
	"/",
	"/non-existing",
	],

	# 3: Test long handles
	[
	"nonreg/" + "x"*100,
	"nonreg/" + "x"*119,
	"nonreg/" + "x"*120,
	"nonreg/" + "x"*121,
	"nonreg/" + "x"*122,
	"nonreg/" + "x"*127,
	"nonreg/" + "x"*128,
	"nonreg/" + "x"*129,
	"nonreg/" + "x"*500,
##	"nonreg/" + "x"*1000,
##	"nonreg/" + "x"*10000,
	],
]


def test(defargs = testsets[0]):
    """Test the HashTable class."""

    import sys
    import getopt

    opts, args = getopt.getopt(sys.argv[1:], '0123af:i:qt:v')

    debug = 0
    timeout = 30
    interval = 5
    filename = None
    types = [HDL_TYPE_URL]
    flags = []

    for o, a in opts:
	if o == '-a': types = []
	if o == '-f': filename = a
	if o == '-i': interval = string.atof(a)
	if o == '-q': debug = 0
	if o == '-t': timeout = string.atof(a)
	if o == '-v': debug = debug + 1
	if o == '-0': args = args + testsets[0]
	if o == '-1': args = args + testsets[1]
	if o == '-2': args = args + testsets[2]
	if o == '-3': args = args + testsets[3]

    if not args:
	args = defargs

    ht = HashTable(filename, debug)

    for hdl in args:
	print "Handle:", `hdl`

	try:
	    replyflags, items = ht.get_data(
		    hdl, types, flags, timeout, interval)
	except Error, msg:
	    print "Error:", msg
	    continue
	except EOFError:
	    print "EOFError"
	    continue

	if debug: print replyflags, items

	bits = 0L
	i = 0
	for c in replyflags:
	    bits = bits | (long(ord(c)) << i)
	    i = i + 8

	print "flags:", hex(bits),
	for i in range(8 * len(replyflags)):
	    if bits & (1L<<i):
		if flags_map.has_key(i):
		    print flags_map[i],
		else:
		    print i,
	print
	print

	print "ADD_HANDLE =", hdl
	if bits & (1L<<HDL_NONMUTABLE): print "\tSTATIC"
	if bits & (1L<<HDL_DISABLED): print "\tDISABLED"

	for stufftype, stuffvalue in items:
	    if data_map.has_key(stufftype):
		s = data_map[stufftype][9:]
	    else:
		s = "UNKNOWN(%d)" % stufftype
	    print "\t%s/%s" % (s, stuffvalue)
	print



if __name__ == '__main__':
    test()
