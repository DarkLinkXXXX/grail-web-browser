"""Configuration object for the printing subsystem.
"""
__version__ = '$Revision: 1.1 $'
#  $Source: /home/john/Code/grail/src/printing/settings.py,v $


_settings = None

def get_settings(prefs=None):
    global _settings
    if not _settings:
	_settings = PrintSettings(prefs)
    return _settings


import grailutil
import string


class PrintSettings:
    """Store the current preference settings."""

    GROUP = 'printing'
    PRINTCMD = "lpr"			# Default print command

    printcmd = None
    printfile = ""
    fileflag = 0
    imageflag = 0
    greyscale = 0
    underflag = 1
    footnoteflag = 1
    fontsize = 10.0
    leading = 10.7
    papersize = "letter"
    orientation = ""
    margins = None
    strip_blanks = 1
    strict_parsing = 0
    user_headers = ()
    postscript_level = 1
    paragraph_indent = 0.0
    # Proper values for a Sun 20" 1152 x 900 pixel display:
    horizontal_scaling = 0.8125
    vertical_scaling = 0.8128

    def __init__(self, prefs):
	"""Load settings and register an interest in updates."""
	self.__prefs = prefs
	if prefs:
	    self.update()
	    prefs.AddGroupCallback(self.GROUP, self.update)
	    prefs.AddGroupCallback('parsing-html', self.update)

    def update(self):
	"""Load / reload settings from preferences subsystem."""
	prefs = self.__prefs
	#
	self.imageflag = prefs.GetBoolean(self.GROUP, 'images')
	self.fileflag = prefs.GetBoolean(self.GROUP, 'to-file')
	self.greyscale = prefs.GetBoolean(self.GROUP, 'greyscale')
	self.footnoteflag = prefs.GetBoolean(self.GROUP, 'footnote-anchors')
	self.underflag = prefs.GetBoolean(self.GROUP, 'underline-anchors')
	self.set_fontsize(prefs.Get(self.GROUP, 'font-size'))
	self.papersize = prefs.Get(self.GROUP, 'paper-size')
	self.orientation = prefs.Get(self.GROUP, 'orientation')
	self.strip_blanks = prefs.GetBoolean(
	    self.GROUP, 'skip-leading-blank-lines')
	self.strict_parsing = prefs.GetBoolean('parsing-html', 'strict')
	self.user_headers = string.split(prefs.Get(self.GROUP, 'user-header'))
	self.postscript_level = prefs.GetInt(self.GROUP, 'postscript-level')
	#
	margins = prefs.Get(self.GROUP, 'margins')
	if margins:
	    self.margins = tuple(map(string.atoi, string.split(margins)))
	self.printcmd = prefs.Get(self.GROUP, 'command') or self.PRINTCMD
	self.paragraph_indent = prefs.GetFloat(self.GROUP, 'paragraph-indent')

    def get_fontsize(self):
	return self.fontsize, self.leading

    def set_fontsize(self, spec):
	"""Set font size and leading based on specification string."""
	self.fontsize, self.leading = grailutil.conv_fontsize(spec)

    def get_fontspec(self):
	if self.fontsize == self.leading:
	    return `self.fontsize`
	return "%s / %s" % (self.fontsize, self.leading)

    def get_scaling(self):
	return self.horizontal_scaling, self.vertical_scaling

    def set_scaling(self, xscaling, yscaling):
	self.horzontal_scaling = xscaling
	self.vertical_scaling = yscaling


#
#  end of file