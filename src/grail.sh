#!/bin/sh

# Grail startup script

# This script tries to set TCL_LIBRARY and TK_ILBRARY to meaningful
# values so that the grail binary can run on systems where Tcl 7.4 and
# Tk 4.0 have not been installed.

# It assumpes that $0 is set to a path leading up to itself and that
# the tksupp directory distributed with grail lives in the same
# directory (this is the way grail is distributed).  If you want to
# install grail differently, you can edit the script or set the
# GRAILDIR environment variable before calling it.

# Guess the grail directory based on $0
case $0 in
  */*): ${GRAILDIR=`echo "$0" | sed 's,/[^/]*$,,' `};;
  *): ${GRAILDIR=.};;
esac

# Compute the pathnames of the support files
BIN=$GRAILDIR/grail.bin
TKSUPP=$GRAILDIR/tksupp

# Test for presence of the grail binary
if test ! -f $BIN
then
  echo "Sorry, I can't find the grail binary $BIN." 1>&2
  echo "Perhaps you haven't installed grail quite right?" 1>&2
  exit 1
fi

# Test for presence of a representative tcl script
if test ! -f $TKSUPP/menu.tcl
then
  echo "Sorry, I can't find the Tcl files I need in $TKSUPP." 1>&2
  echo "Perhaps you haven't installed grail quite right?" 1>&2
  exit 1
fi

# Set the TCL/TK environment variables
TCL_LIBRARY=$TKSUPP
TK_LIBRARY=$TKSUPP
export TCL_LIBRARY
export TK_LIBRARY

# Run the grail binary
exec $BIN ${1+"$@"}
