#! /usr/bin/env python
__version__ = '$Revision: 2.2 $'
#  $Source: /home/john/Code/grail/src/Attic/bookmarks2html.py,v $

import os
import sys

# Path munging
script_name = sys.argv[0]
while 1:
    script_dir = os.path.dirname(script_name)
    if not os.path.islink(script_name):
	break
    script_name = os.path.join(script_dir, os.readlink(script_name))
script_dir = os.path.join(os.getcwd(), script_dir)
script_dir = os.path.normpath(script_dir)
grail_root = script_dir
for path in 'utils', 'pythonlib', 'ancillary', 'sgml_lex', script_dir:
    sys.path.insert(0, os.path.join(grail_root, path))

if sys.version < "1.5":
    import ni

import getopt
import BookmarksParser


def main():
    try:
	opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.error, message:
	usage(2, message)
    for opt, arg in opts:
	if opt in ("-h", "--help"):
	    usage()
    if len(args) > 2:
	usage(2, "too many command line arguments")
    ifn = ofn = '-'
    if args:
	ifn = args[0]
	if ifn != '-':
	    base, ext = os.path.splitext(ifn)
	    ofn = base + ".html"
    if len(args) == 2:
	ofn = args[1]
    if ifn == '-':
	infile = sys.stdin
    else:
	try:
	    infile = open(ifn, 'rb')	# binary in case it's a binary pickle
	except IOError, (errno, message):
	    error(1, "could not open %s: %s" % (ifn, message))
    program = os.path.basename(sys.argv[0])
    format = BookmarksParser.get_format(infile)
    if not format:
	sys.stderr.write(program + ": could not identify input file format")
	sys.exit(1)
    # avoid unneeded conversion: if it's already HTML, just copy it over
    if format[:4] == "html":
	get_outfile(ofn).write(infile.read())
	infile.close()
	return
    parser, writer = BookmarksParser.get_handlers(format, ifn)
    writer = BookmarksParser.GrailBookmarkWriter()
    parser.feed(infile.read())
    parser.close()
    infile.close()
    writer.write_tree(parser._root, get_outfile(ofn))


def get_outfile(ofn):
    if ofn == '-':
	outfile = sys.stdout
    else:
	try:
	    outfile = open(ofn, 'w')
	except IOError, (errno, message):
	    error(1, "could not open %s: %s" % (ofn, message))
	print "Writing output to", ofn
    return outfile


def usage(err=0, message=''):
    program = os.path.basename(sys.argv[0])
    if message:
	print "%s: %s" % (program, message)
	print
    print "usage:", program, "[infile [outfile]]"
    print
    print "\tConvert a Grail bookmarks file to an HTML bookmarks file."
    print
    print "\tIf infile is specified, the default output filename will be"
    print "\tthe name of the input file with the extension '.html'.  If both"
    print "\tinfile and outfile are omitted, input will be read from standard"
    print "\tinput and output will be written to standard output.  A hyphen"
    print "\tmay be used in either position to explicitly request the"
    print "\tcorresponding standard stream."
    sys.exit(err)


def error(err, message):
    program = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: %s\n" % (program, message))
    sys.exit(err)


if __name__ == "__main__":
    main()

#
#  end of file
