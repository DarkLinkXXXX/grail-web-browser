# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:cnri/19980302135001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.4/", or file "LICENSE".

# Import statements needed to help freeze.  Use it as follows:
#
# if 0:
#    import dummies
#
# (These must be two separate lines!)

# Some modules that grail doesn't use but that applets might need
import array
import audioop
import binascii
import imageop
import math
import md5
import struct
import audiodev

# Platform specific modules
import sunaudiodev			# SunOS, Solaris
import al				# SGI

# Standard Applets
import ImageLoopItem

# Standard Protocol Extensions
import httpAPI
import docAPI
import fileAPI
import ftpAPI
import hdlAPI
import logoAPI
import mailtoAPI
import nullAPI

# Standard HTML Extensions
import form
import isindex

# Standard File Type Extensions
import image_gif
