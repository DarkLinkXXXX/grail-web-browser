"""File reader class -- read from a URL to a file in the background."""

from BaseReader import BaseReader

class FileReader(BaseReader):

    """File reader class -- read from a URL to a file in the background.

    Derived classes are supposed to override handle_error() and
    handle_done() to specify what should happen next, and possibly
    handle_meta() to decide whether to continue based on the data
    type.

    The methods handle_data() and handle_eof() are implemented at this
    level and should normally be left alone (or extended, not
    overridden).

    Class or instance variable filemode may be set to override the
    file writing mode (default 'wb' -- make sure it's a writing
    mode!).

    """

    filemode = "wb"

    def __init__(self, browser, api, filename):
	self.filename = filename
	self.fp = None
	BaseReader.__init__(self, browser, api)

    def handle_data(self, data):
	if self.fp is None:
	    try:
		self.fp = open(self.filename, "wb")
	    except IOError, msg:
		self.stop()
		self.handle_error(-1, "IOError", {'detail': msg})
		return
	self.fp.write(data)

    def handle_eof(self):
	if self.fp:
	    self.fp.close()
	self.handle_done()

    def handle_done(self):
	pass


class TempFileReader(FileReader):

    """Derived class of FileReader that chooses a temporary file."""

    def __init__(self, browser, api):
	import tempfile
	filename = tempfile.mktemp()
	FileReader.__init__(self, browser, api, filename)

    def getfilename(self):
	"""New method to return the file name chosen."""
	return self.filename
