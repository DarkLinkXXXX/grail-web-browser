# Some modules that grail doesn't use but that applets might need.
# This is needed to fool freeze; use it as follows:
# if 0:
#    import dummies

import array
import audioop
import binascii
import imageop
import math
import md5
import struct
import audiodev

import ImageLoopItem
import doc

# Platform specific modules
import sunaudiodev			# SunOS, Solaris
import al				# SGI
