#! /usr/bin/env python

# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""Adobe Font Metric conversion script.

This script extracts character width font metrics from Adobe Font
Metric (AFM) files.  Output is suitable for use with Grail's
PostScript printing tools.

Usage: %(program)s [-h] [-d <dir>] <afmfile>

    -h
    --help      -- print this help message

    -d
    --dir <dir> -- directory to write the output file in

    <afmfile>   -- the filename of the file to convert.

Output goes to a file created from the name of the font.  E.g. if the
FontName of the font is Courier-Bold, the output file is named
PSFont_Courier_Bold.py.

"""

import sys
import os
import getopt
import string



program = sys.argv[0]

def usage(status):
    print __doc__ % globals()
    sys.exit(status)


def splitline(line):
    idx = string.find(line, ' ')
    keyword = line[:idx]
    rest = string.strip(line[idx+1:])
    return string.lower(keyword), rest



TEMPLATE = """\
# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

# Character width information for PostScript font `%(fullname)s'
# generated from the Adobe Font Metric file `%(filename)s'.  Adobe
# copyright notice follows:
#
# %(notice)s
#
import PSFont
font = PSFont.PSFont('%(fontname)s', '%(fullname)s',
"""

FORMAT = string.join(['%4d'] * 8, ', ') + ','


def parse(filename, outdir):
    cwidths = [0] * 256
    tdict = {'fontname': '',
	     'fullname': '',
	     'filename': filename,
	     'notice':   '',
	     }

    infp = open(filename, 'r')
    while 1:
	line = infp.readline()
	if line == '':
	    print 'No character metrics found in file:', filename
	    sys.exit(1)
	keyword, rest = splitline(line)
	if keyword in ('fontname', 'fullname', 'notice'):
	    tdict[keyword] = rest
	if keyword == 'startcharmetrics':
	    break
    else:
	print 'No character metrics found in file:', filename
	sys.exit(1)

    outfile = os.path.join(
	outdir,
	string.join(['PSFont'] + string.split(tdict['fontname'], '-'),
		    '_') + '.py')

    # read the character metrics into the list
    while 1:
	line = infp.readline()
	if line == '':
	    break
	keyword, rest = splitline(line)
	if keyword == 'c':
	    info = string.split(rest)
	    charnum = string.atoi(info[0])
	    width = string.atoi(info[3])
	    if 0 <= charnum < 256:
		cwidths[charnum] = width
	if keyword == 'endcharmetrics':
	    break

    infp.close()

    outfp = open(outfile, 'w')
    oldstdout = sys.stdout
    sys.stdout = outfp
    try:
	print TEMPLATE % tdict,
	print '[',
	for i in range(0, 256, 8):
	    if i <> 0:
		print ' ',
	    print FORMAT % tuple(cwidths[i:i+8])
	print '])'
    finally:
	sys.stdout = oldstdout

    outfp.close()



def main():
    help = 0
    status = 0

    try:
	opts, args = getopt.getopt(sys.argv[1:], 'hd:', ['dir', 'help'])
    except getopt.error, msg:
	print msg
	usage(1)

    if len(args) <> 1:
	usage(1)

    filename = args[0]
    outdir = '.'
    for opt, arg in opts:
	if opt in ('-h', '--help'):
	    help = 1
	elif opt in ('-d', '--dir'):
	    outdir = arg

    if help:
	usage(status)

    parse(filename, outdir)

if __name__ == '__main__':
    main()
