"""ArrayIO is no longer faster than StringIO..."""

print "Somebody is importing ArrayIO!  Tell them to use StringIO!"

import StringIO

class ArrayIO(StringIO.StringIO): pass
