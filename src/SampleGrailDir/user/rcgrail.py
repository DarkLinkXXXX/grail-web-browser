#! /depot/sundry/plat/bin/python
#
# Send a remote control command to Grail
#
# Here are a list of the commands understood by the server.  Yes this
# is ad-hoc and will need to be structured in some way in the future.
#
# LOAD URI -- instructs Grail to load the specified URI in one of its
#             browser windows.
#
# LOADNEW URI -- load the specified URI in a new browser window.
#
# To drive this from VM (in XEmacs), add this to your .emacs file:
#
# (setq vm-url-browser "~/.grail/user/rcgrail.py")

import sys
import getopt
import socket
import tempfile
import os

RC_FILENAME = '/tmp/.grail-bwarsaw/:0'
GRAIL_CMD = '/bin/sh'
GRAIL_ARGS = ('-c', '/home/bwarsaw/bin/gograil')
DEFAULT_DISPLAY = ':0'
if os.path.exists('/dev/fb1'):
    DEFAULT_DISPLAY = DEFAULT_DISPLAY + '.1'


def usage(progname):
    print 'Usage:', progname, '[-b] [-h] URI'
    print '    -b fires up a new browser window'
    print '    -h prints this message'
    print '    URI is the URI string to tell Grail to load'

def main():
    progname = sys.argv[0]
    cmd = 'LOAD'
    try:
	optlist, args = getopt.getopt(sys.argv[1:], 'bh')
	if not args:
	    raise getopt.error
	else:
	    uri = args[0]
	for switch, arg in optlist:
	    if switch == '-b':
		cmd = cmd + 'NEW'
	    elif switch == '-h':
		usage(progname)
		sys.exit(0)
	    else:
		raise getopt.error
    except getopt.error:
	usage(progname)
	sys.exit(-1)
    if not os.path.exists(RC_FILENAME):
	# No Grail started yet, try starting it up...
	if not os.fork():
	    os.environ['DISPLAY'] = DEFAULT_DISPLAY
	    os.execvpe(GRAIL_CMD, GRAIL_ARGS + (uri,), os.environ)
	else:
	    sys.exit(0)
    # calculate the command
    cmd = cmd + ' ' + uri
    # now do the remote connection and command
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(RC_FILENAME)
    s.send(cmd)
    s.close()

main()
