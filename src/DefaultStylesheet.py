"""Default style sheet for Grail's Viewer widget.

This class has no methods, only class variables.  It is not intended
to be instantiated; rather, you pass the class itself as the
stylesheet argument to the Viewer browser.  It is useful to inherit
from it though, if you want to define a style sheet that is just a
little bit different.

"""


# XXX This needs reworking:
# - Those paragraph styles that define a font
# need to set their own variants on char styles
# Suggest to name those e.g. "h1.bold"
# - Possibly need to make formal distinction between font settings
# and other settings for a style
# - Para styles can be nested (e.g. <LI> ... <H1> ...)
# - List bullets need to be treated differently


class DefaultStylesheet:
    default = {
	'font': '-*-helvetica-medium-r-normal-*-*-100-100-*-*-*-*-*',
	}

    para_styles = {
	'h1': {
	    'font': '-*-helvetica-bold-r-normal-*-*-180-100-*-*-*-*-*',
	    'spacing1': 20,
	    'spacing3': 10,
	    },
	'h2': {
	    'font': '-*-helvetica-bold-r-normal-*-*-140-100-*-*-*-*-*',
	    'spacing1': 15,
	    'spacing3': 10,
	    },
	'h3': {
	    'font': '-*-helvetica-bold-r-normal-*-*-120-100-*-*-*-*-*',
	    'spacing1': 10,
	    'spacing3': 5,
	    },
	'h4': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-100-*-*-*-*-*',
	    'spacing1': 10,
	    'spacing3': 3,
	    },
	'h5': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-100-*-*-*-*-*',
	    'spacing1': 6,
	    'spacing3': 2,
	    },
	'h6': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-100-*-*-*-*-*',
	    'spacing1': 4,
	    'spacing3': 2,
	    },
	'li1': {
	    'lmargin1': 20,
	    'lmargin2': 30,
	    },
	'li2': {
	    'lmargin1': 40,
	    'lmargin2': 50,
	    },
	'li3': {
	    'lmargin1': 60,
	    'lmargin2': 70,
	    },
	'li4': {
	    'lmargin1': 80,
	    'lmargin2': 90,
	    },
	'li5': {
	    'lmargin1': 100,
	    'lmargin2': 110,
	    },
	'li6': {
	    'lmargin1': 120,
	    'lmargin2': 130,
	    },
	'pre': {
	    'font': '-*-courier-medium-r-normal-*-*-100-100-*-*-*-*-*',
	    },
	}

    char_styles = {
	1: {
	    'font': '-*-helvetica-medium-o-normal-*-*-100-100-*-*-*-*-*',
	    },
	2: {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-100-*-*-*-*-*',
	    },
	3: {
	    'font': '-*-courier-medium-r-normal-*-*-100-100-*-*-*-*-*',
	    },
	'a': {
	    'foreground': 'blue',
##	    'underline': 'on',		# This is ugly
	    },
	}
