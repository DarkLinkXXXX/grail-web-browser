#! /usr/bin/env python

# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""Handle Management System client library.

This module implements the low-level client library for CNRI's Handle
Management System.  For general info about handles, see
http://www.handle.net/.  This module was built using the Handle
Resolution Protocol Specification at
http://www.handle.net/docs/client_spec.html, and inspection of (an
earlier version of) the client library sources.

Classes:

- Error -- exception for error conditions specific to this module 
- PacketPacker -- helper for packet packing
- PacketUnpacker -- helper for packet unpacking
- SessionTag -- helper for session tag management
- HashTable -- hash table

TO DO, doubts, questions:

XXX We don't use cache servers nor do we download the hash table from
    the server.

XXX Constants should only have a prefix 'HP_' or 'HDL_' when their
    name occurs in the spec.  I've tried to fix this but may have
    missed some cases.

XXX Should break up get_data in send_request and poll_request.

XXX When retrying, should we generate a new tag or reuse the old one?
    (new -- let's not confuse ourselves further)

XXX When an incomplete result is returned, should we raise an exception?
    (yes)

XXX Should we cache the hash table entries read from the file?
    (yes)

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


# Internal constants
# XXX These need reorganizing
HASH_TABLE_FILE_FALLBACK = 'hdl_hash.tbl'
DEFAULT_SERVERS = ['132.151.1.155',
		   '198.32.1.37',
		   '132.151.1.159',
		   '198.32.1.73']
DEFAULT_NUM_OF_BITS = 2
DEFAULT_HASH_FILE = '/etc/hdl_hash.tbl'
DEFAULT_UDP_PORT = 2222
DEFAULT_TCP_PORT = 2222
DEFAULT_ADMIN_PORT = 2223
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



# Flag bits
HDL_NONMUTABLE = 0			# LSB (0th bit)
HDL_DISABLED = 1			# (1st bit)
flags_map = {0: 'HDL_NONMUTABLE', 1: 'HDL_DISABLED'}

# Handle protocol miscellaneous constants
HP_VERSION = 1				# Handle protocol version

# Handle protocol lengths
HP_HEADER_LENGTH = 28			# Packet header length
HP_MAX_COMMAND_SIZE = 512		# Max command packet length
HP_MAX_DATA_VALUE_LENGTH = 128
HP_HASH_HEADER_SIZE = 36

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
HDL_TYPE_INET_HOST = 4			# Internet host name or IP address
HDL_TYPE_INET_SERVICE = 5		# "hostname":"tcp"|"udp":"port"
HDL_TYPE_CONTACT_INFO = 6		# Same Syntax As EMAIL_RFC822
HDL_TYPE_DLS = 7			# To be determined
HDL_TYPE_CACHE_PERIOD = 8		# Default caching period timeout
HDL_TYPE_HANDLE_TYPE = 9		# For Handle Service internal use
HDL_TYPE_SERVICE_HANDLE = 10		# Handle containing hash table info
HDL_TYPE_SERVICE_POINTER  = 11		# Service's hash table info
# Non-registered types are > 65535
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
HP_PARSING_FAILURE = 1
HP_VERSION_MISMATCH = 2
HP_ACCESS_TEMPORARILY_DENIED = 3
HP_NOT_RESPONSIBLE_FOR_HANDLE = 4
HP_HANDLE_NOT_FOUND = 5
HP_FORWARDED = 6
HP_INTERNAL_ERROR = 7
HP_TYPES_NOT_FOUND = 8
HP_REQUEST_TIMED_OUT = 9
HP_HANDLE_DOES_NOT_EXIST = 10
HP_FORWARD_ERROR = 11
"""

# See data_types comment above
exec error_codes
error_map = {}
exec error_codes in error_map
for key, value in error_map.items():
    if key != '__builtins__':
	error_map[value] = key

# Error code set by the parser
HDL_ERR_INTERNAL_ERROR = HP_INTERNAL_ERROR


# error class for this module
class Error:
    """Exception class for module hdllib."""
    def __init__(self, msg=None):
	self.msg = msg
    def __repr__(self):
	return repr(self.msg)
    def __str__(self):
	return str(self.msg)



class PacketPacker:
    """Helper class to pack packets."""
    def __init__(self):
	self.p = xdrlib.Packer()

    def pack_header(self, tag=0, command=HP_QUERY, err=0, sequence=1,
		   total=1, version=HP_VERSION):
	"""Pack the packet header (except the body length).

	The argument order differs from the order in the
	packet header so we can use defaults for most fields.

	"""
	self.p.pack_uint(version)
	self.p.pack_uint(tag)
	self.p.pack_uint(command)
	self.p.pack_uint(sequence)
	self.p.pack_uint(total)
	self.p.pack_int(err)

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

	body = p.get_buffer()

	self.p.pack_string(body)

    def get_buffer(self):
	return self.p.get_buffer()



class PacketUnpacker:
    """Helper class to unpack packets."""

    def __init__(self, data, debug=0):
	# Set the debug ivar and call the init stuff
	# needed by xdrlib.Unpacker.
	self.debug = debug
	self.u = xdrlib.Unpacker(data)
	
    def buf(self):
	try:
	    return self.u.get_buffer()
	except AttributeError:
	    # TBD: digusting hack made necessary by a missing
	    # interface in xdrlib.Unpacker to get either the buffer or
	    # the length of the remaining buffer.  this requires
	    # knowledge of Python 1.4's name munging scheme so we can
	    # peek at this object's private attribute.  This will be
	    # fixed in Python 1.5.
	    return self.u._Unpacker__buf

    def unpack_header(self):
	"""Unpack a packet header (except the body length).

	The argument order corresponds to the arguments to
	packheader().

	"""
	version = self.u.unpack_uint()
	tag = self.u.unpack_uint()
	command = self.u.unpack_uint()
	sequence = self.u.unpack_uint()
	total = self.u.unpack_uint()
	err = self.u.unpack_int()

	return (tag, command, err, sequence, total, version)

    def check_body_length(self):
	"""Check that the body length matches what the header says.

	Set self.total_length.  If it doesn't, raise Error.

	"""
	self.length_from_header = self.u.unpack_uint()
	if len(self.buf()) - self.u.get_position() != self.length_from_header:
	    print "length according to header:",
	    print self.length_from_header,
	    print "actual length:",
	    print len(buf) - self.u.get_position()
	    raise Error("body length mismatch")

    def unpack_item_array(self):
	"""Unpack an array of (type, value) pairs."""
	nopts = self.u.unpack_uint()
	opts = []
	for i in range(nopts):
	    opt = self.u.unpack_uint()
	    val = self.u.unpack_opaque()
	    opts.append((opt, val))
	return opts
	
    def unpack_item_array_cont_chk(self, start):
	"""Unpack an array of (type, value) pairs.

	Check to see if there is a continuation
	for this packet or if this *is* a continuation
	packet itself.

	"""
	nopts = self.u.unpack_uint()
	if self.debug: print 'nopts=' + str(nopts)
	opts = []
	for i in range(nopts):
	    opt = self.u.unpack_uint()
	    if self.debug: print 'type=' + str(opt)
	    #
	    # Unpack the length value to determine if we have
	    # a continuation packet.
	    #
	    length_from_body = self.u.unpack_int()
	    if self.debug: print 'length from body=' + str(length_from_body)
	    if length_from_body == 0:
		raise Error("Invalid zero packet length")
	    #
	    # If length_from_body < 0 , we've found a continuation
	    # packet.  Pull off an additional field containing the
	    # beginning offset in the buffer.
	    #
	    if length_from_body < 0:
		total_length = length_from_body * -1
		offset = self.u.unpack_uint()
		if self.debug: print 'Continuation packet'
		if offset < 0 or offset > total_length:
		    error = 'Bad offset in UDP body: ' + str(offset)
		    raise Error(error)
		if nopts > 1:
		    # Found the end of a continuation packet
		    self.value_length = total_length - offset
		else:
		    # The entire packet is a continuation (16 is the number of
		    # bytes in an md5 checksum...  this will never change or if
		    # it does it will be called 'md6'...)
		    #
		    self.value_length = len(self.buf()) \
					- self.u.get_position() - 16
		# Change opt to be negative flagging this as a continuation 
		opt = opt * -1

	    else:
		# Normal packet, but it may be the start of a continuation
		if self.debug: print 'Normal Packet'
		total_length = self.value_length = length_from_body
		if self.debug: print "length from body =", length_from_body
		if nopts == 1:
		    max_value_length = len(self.buf()) \
				       - self.u.get_position() - 16
		    if self.value_length > max_value_length:
			if self.debug:
			    print 'Start of a continuation:',
			    print "max value length =", max_value_length
			self.value_length = max_value_length
		#
		# Finally get the value
		if self.debug: print 'Getting data segment of ' \
		   + str(self.value_length) + ' bytes'
	    value = self.u.unpack_fstring(self.value_length)
	    if self.debug: print "Got", len(value), "bytes:", `value`
	    opts.append((opt, value))
	return opts

    def set_debug(self):
	"""Increment the debug ivar."""
	self.debug = self.debug + 1
	
    def unpack_request_body(self):
	"""Unpack a request body (preceded by its length)."""

	self.check_body_length()

	hdl = self.u.unpack_string()

	options = self.u.unpack_item_array()

	ntypes = self.u.unpack_uint()
	types = []
	for i in range(ntypes):
	    types.append(self.u.unpack_uint())

	replyport = self.u.unpack_uint()
	replyaddr = self.u.unpack_opaque()

	return (hdl, options, types, replyport, replyaddr)

    def unpack_reply_body(self):
	"""Unpack a reply body (preceded by its length).

	Make sure the checksum is correct, else raise Error.

	"""

	self.check_body_length()

	start = self.u.get_position()

	flags = self.u.unpack_opaque()
	
	items = self.unpack_item_array_cont_chk(start)

	checksum = self.u.unpack_fopaque(16)
	digest = md5.new(self.buf()[start:-16]).digest()

	if digest != checksum:
	    raise Error("body checksum mismatch")
	return flags, items

    def unpack_error_body(self, err):
	"""Unpack an error reply body according to the error code."""

	# XXX It would be convenient if the error code was saved as an
	# XXX ivar by unpack_header().

	self.check_body_length()

	if err == HP_NOT_RESPONSIBLE_FOR_HANDLE:
	    server = self.u.unpack_string()
	    udpport = self.u.unpack_int()
	    tcpport = self.u.unpack_int()
	    return (server, udpport, tcpport)
	elif err == HP_FORWARD_ERROR:
	    return self.u.unpack_string()
	elif err == HP_VERSION_MISMATCH:
	    return self.u.unpack_int()
	elif err == HP_ACCESS_TEMPORARILY_DENIED:
	    return self.u.unpack_string()
	elif err == HP_PARSING_FAILURE:
	    return self.u.unpack_string()
	else:
	    # According to the spec, the other errors have no other
	    # information associated with them.
	    return None


class SessionTag:
    """Session tag.  See client library equivalent in
    create_tag.c: create_session_tag().

    Methods:

    session_tag() -- get next session tag

    XXX looks pretty bogus to me (time modulo pid??? gimme a break)
    XXX (and why does it have to be a class anyway?)

    """
    def session_tag(self):
	"""Implemented as in create_session_tag()."""
	now = time.time()
	try: seed = now % os.getpid()
	except: seed = now
	rand.srand(int(seed))
	return rand.rand()



class HashTable:
    """Hash table.

    Public methods:

    - __init__([filename, [debug, [server]]]) -- constructor
    - set_debuglevel(debug) -- set debug level
    - hash_handle(hdl) -- hash a handle to handle server info
    - get_data(hdl, [types, [flags, [timeout, [interval]]]]]) --
      resolve a handle

    """	
    def __init__(self, filename = None, debug = None, server = None):
	"""Hash table constructor.

	Read the hash table file header from optional filename and
	hold on to the open file.  Store the header fields as instance
	variables.  Optional debug argument sets debugging level.

	If filename is None and the optional server argument is given,
	a single bucket hash table is constructed using the default
	port and the given server.

	If both filename and server are none, we try to load a hash
	table from the default location or from the fallback location,
	and if both fail, we construct one using hardcoded defaults.

	XXX This has only been tested with the default hash table at
	"ftp://cnri.reston.va.us/handles/client_library/hdl_hash.tbl;type=i"
	which (at the time of writing) has schema version 1.

	Exceptions:

	- Error
	- IOError
	- whatever xdrlib raises

	"""

	if debug is None: debug = DEBUG
	self.debug = debug

	self.tag = SessionTag()

	self.bucket_cache = {}

	if filename:
	    self._read_hash_table(filename)
	elif server:
	    self._set_hardcoded_hash_table(server)
	else:
	    for fn in (DEFAULT_HASH_FILE, HASH_TABLE_FILE_FALLBACK):
		try:
		    self._read_hash_table(fn)
		except IOError, msg:
		    if self.debug:
			print "IOError for %s: %s" % (`fn`, str(msg))
		else:
		    break
	    else:
		self._set_hardcoded_hash_table()


    def _set_hardcoded_hash_table(self, server=None):
	"""Construct a hardcoded hash table -- internal.

	If the server argument is given, construct a single bucket
	from it using the default ports.  If the server argument is
	absent, construct a number of buckets using the default ports
	and the list of default servers.

	"""
	if self.debug:
	    if server:
		print "Constructing hardcoded hash table using", server
	    else:
		print "Constructing hardcoded fallback hash table"
	if server:
	    self.num_of_bits = 0
	else:
	    self.num_of_bits = DEFAULT_NUM_OF_BITS
	up = DEFAULT_UDP_PORT
	tp = DEFAULT_TCP_PORT
	ap = DEFAULT_ADMIN_PORT
	for i in range(1<<self.num_of_bits):
	    s = server or DEFAULT_SERVERS[i]
	    if self.debug and not server:
		print 'Bucket', i, 'uses server', s
	    self.bucket_cache[i] = (0, 0, s, up, tp, ap, -1)


    def _read_hash_table(self, filename):
	"""Read the hash table from a given filename -- internal.

	Raise IOError if the file can't be opened or if the MD5
	checksum is invalid.  Raise EOFError if xdrlib finds a
	problem.

	If the file is valid, set a bunch of ivars to info read from
	the hash table header, and set self.fp to the (still open)
	hash table file.

	"""
	if self.debug: print "Opening hash table:", `filename`
	self.fp = fp = open(filename, 'rb')

	# Verify the checksum before proceeding
	checksum = fp.read(16)
	if md5.new(fp.read()).digest() != checksum:
	    fp.close()
	    raise IOError, "checksum error for hash table " + filename

	# Seek back to start of header
	fp.seek(16)

	# Read and decode header
	u = xdrlib.Unpacker(fp.read(4))
	self.schema_version = u.unpack_int()
	# The header_length field is not present if schema version < 2
	if self.schema_version < 2:
	    if self.debug: print "*** Old hash table detected ***"
	    self.header_length = HP_HASH_HEADER_SIZE
	else:
	    u = xdrlib.Unpacker(fp.read(4))
	    self.header_length = u.unpack_int()
	u = xdrlib.Unpacker(fp.read(self.header_length - 4))
	self.data_version = u.unpack_int()
	self.num_of_bits = u.unpack_int()
	self.max_slot_size = u.unpack_int()
	self.max_address_length = u.unpack_int()
	self.unique_id = u.unpack_fopaque(16)

	if self.debug:
	    print '*'*20
	    print "Hash table file header:"
	    print "Schema version:", self.schema_version
	    print "header length: ", self.header_length
	    print "data version:  ", self.data_version
	    print "num_of_bits:   ", self.num_of_bits
	    print "max slot size: ", self.max_slot_size
	    print "max IP addr sz:", self.max_address_length
	    print "unique ID:     ", hexstr(self.unique_id)
	    print '*'*20

	# Calculate file offset of first bucket
	self.bucket_offset = 16 + self.header_length


    def set_debuglevel(self, debug):
	"""Set the debug level to LEVEL."""
	self.debug = debug


    def hash_handle(self, hdl):
	"""Hash a HANDLE to a tuple of handle server info.

	Return an 8-tuple containing the bucket fields:
	    slot no
	    weight
	    ipaddr (transformed to a string in dot notation)
	    udp query port
	    tcp query port
	    admin port
	    secondary slot no

	A leading "//" is stripped from the handle and it is
	converted to upper case before taking its MD-5 digest.
	The first 'num_of_bits' bits of the digest are then used to
	compute the hash table bucket index; the selected
	bucket is read from the hash table file and decoded --
	or if it is already in the bucket cache we return that.

	Exceptions may be raised by xdrlib if the entry is
	corrupt.

	"""

	if self.num_of_bits > 0:
	    if hdl[:2] == '//': hdl = hdl[2:]
	    hdl = string.upper(hdl)
	    digest = md5.new(hdl).digest()
	    u = xdrlib.Unpacker(digest)
	    index = u.unpack_uint()
	    index = int(index >> (32 - self.num_of_bits))
	else:
	    index = 0

	if self.bucket_cache.has_key(index):
	    if self.debug: print "return cached bucket for index", index
	    return self.bucket_cache[index]

	pos = self.bucket_offset + (index * self.max_slot_size)
	self.fp.seek(pos)

	entry = self.fp.read(self.max_slot_size)
	u = xdrlib.Unpacker(entry)

	slot_no = u.unpack_int()
	weight = u.unpack_int()
	ip_address = u.unpack_opaque()
	udp_query_port = u.unpack_int()
	tcp_query_port = u.unpack_int()
	admin_port = u.unpack_int()
	secondary_slot_no = u.unpack_int()

	ipaddr = string.joinfields(map(repr, map(ord, ip_address)), '.')

	if self.debug:
	    print "="*20
	    print "Hash bucket index:", index
	    print "slot_no:          ", slot_no
	    print "weight:           ", weight
	    print "ip_address:       ", hexstr(ip_address)
	    print "decoded IP addr:  ", ipaddr
	    print "udp_query_port:   ", udp_query_port
	    print "tcp_query_port:   ", tcp_query_port
	    print "admin_port:       ", admin_port
	    print "secondary_slot_no:", secondary_slot_no
	    print "="*20

	result = (slot_no, weight, ipaddr, udp_query_port,
		  tcp_query_port, admin_port, secondary_slot_no)
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
	request = p.get_buffer()

	(server, qport) = self.hash_handle(hdl)[2:4]

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
	    u = PacketUnpacker(reply, self.debug)
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

	    if not 1 <= sequence <= total and not err:
		if self.debug: print "bad sequence number"
		continue

	    expected = total
	    
	    if err != HP_OK:
		if self.debug:
		    print 'err: ', err
		err_info = u.unpack_error_body(err)
		if self.debug:
		    print 'err_info:', `err_info`
		try:
		    err_name = error_map[err]
		except KeyError:
		    err_name = str(err)
		if self.debug:
		    print 'err_name:', `err`
		raise Error((err, err_name, err_info))

	    flags, items = u.unpack_reply_body()

	    responses[sequence] = (flags, items)

	s.close()

	allflags = None
	allitems = []
	for i in range(1, expected+1):
	    if responses.has_key(i):
		(flags, items) = responses[i]
		item = items[0]
		#
		# Check for a continuation packet, if we find one,
		# append it to the previous
		if item[0] < 0:
		    error = "Internal error assembling continuation packets"
		    try:
			previtem = allitems[-1]
		    except IndexError:
			raise IOError, error
		    if abs(item[0]) != previtem[0]:
			raise IOError, error
		    newdata = previtem[1] + item[1]
		    previtem = (previtem[0], newdata)
		    allitems[-1] = previtem
		else:
		    # Normal packet
		    allflags = flags
		    allitems = allitems + items
	return (allflags, allitems)


# Convert a string to hex
def hexstr(s):
    return "%02x"*len(s) % tuple(map(ord, s))


# Test sets

testsets = [
	# 0: Official demo handle (with and without //)
	[
	"//cnri-1/cnri_home",
	"cnri-1/cnri_home",
	],
	# 1: Some demo handles
	[
	"cnri.dlib/december95",
	"cnri.dlib/november95",
	"CNRI.License/Grail-Version-0.3",
	"CNRI/19970131120000",
	"CNRI/19970131120001",
	#"nonreg.guido/python-home-web-site",
	#"nonreg.guido/python-home-page",
	#"nonreg.guido/python-home-ftp-dir",
	#"nonreg.guido/python-ftp-dir",
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

	# 4: Test handles on local handle server.
	# The last three handles are known to exploit the poll_data.c
	# bug discovered by Charles on 2/26/96.
	[
	"nlm.hdl_test/96053804",
	"nlm.hdl_test/96047983",
	"nlm.hdl_test/96058248",
	"nlm.hdl_test/96037846",
	"nlm.hdl_test/96055523",
	],
]


def test(defargs = testsets[0]):
    """Test the HashTable class."""

    import sys
    import getopt

    try:
	opts, args = getopt.getopt(sys.argv[1:], '01234af:i:qs:t:v')
    except getopt.error, msg:
	print msg
	sys.exit(2)

    debug = 0
    timeout = 30
    interval = 5
    filename = None
    types = [HDL_TYPE_URL]
    flags = []
    server = None
    
    for o, a in opts:
	if o == '-a': types = []
	if o == '-f': filename = a
	if o == '-i': interval = string.atof(a)
	if o == '-q': debug = 0
	if o == '-t': timeout = string.atof(a)
	if o == '-s': server = a
	if o == '-v': debug = debug + 1
	if o == '-0': args = args + testsets[0]
	if o == '-1': args = args + testsets[1]
	if o == '-2': args = args + testsets[2]
	if o == '-3': args = args + testsets[3]
	if o == '-4':
	    if not args: args = testsets[4]
	    if not server: server = 'gather.cnri.reston.va.us'
	    if types: types.append(HDL_TYPE_DLS)

    if not args:
	args = defargs

    ht = HashTable(filename, debug, server)

    for hdl in args:
	print "Handle:", `hdl`

	try:
	    replyflags, items = ht.get_data(
		    hdl, types, flags, timeout, interval)
	except Error, msg:
	    print "Error:", msg
	    print
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

	if bits & (1L<<HDL_NONMUTABLE): print "\tSTATIC"
	if bits & (1L<<HDL_DISABLED): print "\tDISABLED"

	for stufftype, stuffvalue in items:
	    if stufftype in (HDL_TYPE_SERVICE_POINTER,
			     HDL_TYPE_SERVICE_HANDLE):
		stuffvalue = hexstr(stuffvalue)
	    if data_map.has_key(stufftype):
		s = data_map[stufftype][9:]
	    else:
		s = "UNKNOWN(%d)" % stufftype
	    print "\t%s/%s" % (s, stuffvalue)
	print


if __name__ == '__main__':
    test()
