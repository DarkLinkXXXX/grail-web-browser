# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""The doi: scheme is an alias to the hdl: scheme in CNRI's Navigator/IE
extensions.  This causes the same thing to work in Grail."""

__version__ = '$Revision: 2.2 $'


import hdlAPI

doi_access = hdlAPI.hdl_access
