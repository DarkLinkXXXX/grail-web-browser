# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".

# Trivial assertion function

class AssertionError:
    def __init__(self, msg):
    	self.msg = msg
    def __str__(self):
    	return str(self.msg)

def Assert(cond, msg="assertion failed (see traceback)"):
    if not cond: raise AssertionError(msg)
