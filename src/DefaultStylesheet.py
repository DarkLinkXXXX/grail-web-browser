"""Default style sheet for Grail's Viewer widget.

This class has no methods, only class variables.  It is not intended
to be instantiated; rather, you pass the class itself as the
stylesheet argument to the Viewer browser.  It is useful to inherit
from it though, if you want to define a style sheet that is just a
little bit different.

"""


class DefaultStylesheet:

    # Default settings (text widget configure)
    default = {
	'font': '-*-helvetica-medium-r-normal-*-*-120-*-*-*-*-*-*',
	}

    styles = {

	# Header fonts

	'h1_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-180-*-*-*-*-*-*',
	    },
	'h2_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-140-*-*-*-*-*-*',
	    },
	'h3_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-120-*-*-*-*-*-*',
	    },
	'h4_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-*-*-*-*-*-*',
	    },
	'h5_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-*-*-*-*-*-*',
	    },
	'h6_b': {
	    'font': '-*-helvetica-bold-r-normal-*-*-100-*-*-*-*-*-*',
	    },

	# Normal fonts

	'_i': {
	    'font':  '-*-helvetica-medium-o-normal-*-*-120-*-*-*-*-*-*',
	    },
	'_b': {
	    'font':  '-*-helvetica-bold-r-normal-*-*-120-*-*-*-*-*-*',
	    },
	'_b_i': {
	    'font':  '-*-helvetica-bold-o-normal-*-*-120-*-*-*-*-*-*',
	    },

	# Typewriter fonts

	'_tt': {
	    'font': '-*-courier-medium-r-normal-*-*-120-*-*-*-*-*-*',
	    },
	'_tt_i': {
	    'font': '-*-courier-medium-o-normal-*-*-120-*-*-*-*-*-*',
	    },
	'_tt_b': {
	    'font': '-*-courier-bold-r-normal-*-*-120-*-*-*-*-*-*',
	    },
	'_tt_b_i': {
	    'font': '-*-courier-bold-o-normal-*-*-120-*-*-*-*-*-*',
	    },

	# Anchors

	'a': {
	    'foreground': 'blue',
	    'underline': 'true',
	    },

	# Preformatted text
	'pre': {
	    'wrap': 'none',
	    },

	# Centered text
	'center': {
	    'justify': 'center',
	    },

	}

    history = {

	# Anchors

	'ahist': {
	    'foreground': 'blue4',
	    'underline': 'true',
	    },

	'atemp': {
	    'foreground': 'red',
	    'underline': 'true',
	    },

	}

    priorities = {

	'ahist': 'a',
	'atemp': 'ahist',

	}
