"""ArrayIO is no longer faster than StringIO..."""

import StringIO

class ArrayIO(StringIO.StringIO): pass
