# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

# Trivial assertion function

class AssertionError:
    def __init__(self, msg):
    	self.msg = msg
    def __str__(self):
    	return str(self.msg)

def assert(cond, msg = "assertion failed (see traceback)"):
    if not cond: raise AssertionError(msg)
