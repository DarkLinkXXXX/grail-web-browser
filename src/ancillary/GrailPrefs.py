"""Functional interface to Grail user preferences.

There are two preferences files.  The system-wide defaults file is located
in the grail root directory, and named "grail-defaults".  The user's custom
preferences, whose settings supercede ones from the system preferences, is
in the directory named by grailutil.getgraildir().

Interrogation for preferences which have no set value provokes a KeyError
exception.

	Preferences file format:

Preferences files contain string name/value pairs, delimited like rfc822
header fields.  Most lines start with non-whitespace alphanumerics - the
header-field name - followed immediately by a ':'.  Typically, whitespace
follows and then the value for that field.

There are also continuation lines, which begin with whitespace, but also
contain non-whitespace.  These lines continue the value for the most recent
line with a header-field name.

Preference key names are derived by dividing header-field names into two
parts, a group name and a preference name.  The two parts are represented
in the header-field name delimited by '--' a pair of dashes.  Preference
key names are case insensitive.

The first line in a preferences file containing only white-space terminates
the preferences, and a warning is emitted to stderr if there are any
subsequent non-blank lines.

Comments can be included in a preferences file by using header-style lines
where the header-field name does *not* contain a '--' pair of dashes.

Here is an example of a small preferences file:

C: Comment lines here begin with "C:".
landmarks--grail-home-page:	http://monty.cnri.reston.va.us/grail-0.2/
C: Pref ('landmarks', 'home-page') with empty value:
landmarks--home-page:
C: Pref with value on continuation line (this comment cannot be between!):
presentation--message-font:
	-*-helvetica-medium-r-normal-*-*-100-100-*-*-*-*-*
browser--default-height:	40
"""

# Todo:
#  - Preference-change callback funcs

__version__ = "$Revision: 2.5 $"
# $Source: /home/john/Code/grail/src/ancillary/Attic/GrailPrefs.py,v $

import os
import sys
import string
import rfc822
if __name__ == "__main__":
    sys.path.insert(0, '../utils')
import grailutil

USERPREFSFILENAME = 'grail-preferences'
SYSPREFSFILENAME = 'grail-defaults'

verbose = 0

class Preferences:
    """Get and set fields in a customization-values file."""

    # We maintain an rfc822 snapshot of the file, which we read only once,
    # and a dict, for new values.

    def __init__(self, filename, readonly=0):
	"""Initiate from FILENAME with MODE (default 'r' read-only)."""
	self._filename = filename
	try:
	    f = open(filename)
	except IOError:
	    f = None
	if f:
	    self._last_mtime = os.stat(filename)[9]
	    self._db = rfc822.Message(f)
	    self._new = {}
	    # Check for content misplaced after first blank line:
	    residue = string.strip(f.read())
	    if residue:
		sys.stderr.write("Ignoring preferences following blank line"
				 + " in %s\n" % f.name)
	    f.close()
	else:
	    self.file_mtime = 0
	    self._db = None
	    self._new = {}
	self._modified = 0

    def Get(self, group, pref):
	"""Get preference in GROUP with NAME, or raise KeyError if none."""
	key = self._make_key(group, pref)
	if self._new.has_key(key):
	    return self._new[key]
	else:
	    try:
		if not self._db:
		    raise KeyError
		else:
		    return self._db[key]
	    except KeyError:
		raise KeyError, "Preference %s not found" % ((group, pref),)

    def Set(self, group, pref, val):
	"""Set GROUP PREFERENCE to VALUE.  Return true iff successful."""
	self._modified = 1
	self._new[self._make_key(group, pref)] = str(val)

    def Tampered(self):
	"""Has the file been externally modified?"""
	return os.stat(self._filename)[9] != self.mtime

    def Editable(self):
	"""Ensure that the user has a graildir and it is editable."""
	if not grailutil.establish_dir(os.path.split(self._filename)[0]):
	    return 0
	elif os.path.exists(self._filename):
	    return 1
	else:
	    try:
		tempf = open(self._filename, 'a')
		tempf.close()
		return 1
	    except os.error:
		return 0

    def NeedsSave(self): return self._modified and 1

    def Save(self):
	"""Write the preferences out to file, return true if successful.

	User is responsible for ensuring that the file is self.Editable(),
	and it has not been self.Tampered()."""
	try: os.rename(self._filename, self._filename + '.bak')
	except os.error: pass		# No file to backup.

	try:
	    fp = open(self._filename, 'w')
	    did = {}
	    new = self._new
	    if self._db:
		for header in self._db.headers:
		    k = string.split(header, ':')[0]
		    if new.has_key(k):
			fp.write(k + ': ' + new[k])
		    else:
			fp.write(header)
		    did[k] = 0
	    for k, v in new.items():
		if not did.has_key(k):
		    fp.write(k + ': ' + new[k])
	    fp.close()
	    self._modified = 0
	    return 1
	except IOError:
	    return 0

    def _make_key(self, group, pref):
	"""Produce a key from preference GROUP and NAME strings."""
	return string.lower(group + '--' + pref)
		    
class AllPreferences:
    """Maintain the combination of user and system preferences."""
    def __init__(self):
	self._user = Preferences(os.path.join(grailutil.getgraildir(),
					      USERPREFSFILENAME))
	from __main__ import grail_root
	self._sys = Preferences(os.path.join(grail_root, SYSPREFSFILENAME), 1)

    # Getting utensils.

    def Get(self, group, pref):
	"""Get pref in GROUP with NAME, trying the user than the sys prefs.

	Or raise KeyError if not found."""
	try:
	    return self._user.Get(group, pref)
	except KeyError:
	    return self._sys.Get(group, pref)

    def _GetTyped(self, group, pref, cvrtr, type_name):
	"""Get preference, using CONVERTER to convert to type NAME.

	Raise KeyError if not found, TypeError if value is wrong type."""
	val = self.Get(group, pref)
	try:
	    return cvrtr(val)
	except ValueError:
	    raise TypeError, ('%s not %s: %s'
			       % (str((group, pref)), type_name, `val`))

    def GetInt(self, group, pref):
	return self._GetTyped(group, pref, string.atoi, "integer")
    def GetFloat(self, group, pref):
	return self._GetTyped(group, pref, string.atof, "float")
    def GetBoolean(self, group, pref):
	got = self._GetTyped(group, pref, string.atoi, "Boolean")
	if got not in (0, 1):
	    raise TypeError, ('%s not %s: %s'
			      % ((group, pref), "Boolean", `got`))
	return got

    # Editing utensils.

    def Set(self, group, pref, val):
	"""Assign GROUP PREFERENCE with VALUE."""
	self._user.Set(group, pref, val)

    def Editable(self):
	"""Identify or establish user's prefs file, or IO error."""
	return self._user.Editable()

    def Tampered(self):
	"""True if user prefs file modified since we read them."""
	return self._user.Tampered()

    def NeedsSave(self): return self._user.NeedsSave()

    def Save(self):
	"""Write the preferences out to file, return true if successful."""
	if not self._user.Editable():
	    raise IOError, 'Unable to get user prefs ' + self._user._filename
	return self._user.Save()

def test():
    """Exercise preferences mechanisms."""
    sys.path.insert(0, "../utils")
    from testing import exercise
    
    env = sys.modules[__name__].__dict__

    # Reading the db:
    exercise("prefs = AllPreferences()", env, "Suck in the prefs")

    # Getting values:
    exercise("origin = prefs.Get('landmarks', 'grail-home-page')", env,
	     "Get an existing plain pref.")
    exercise("height = prefs.GetInt('browser', 'default-height')", env,
	     "Get an existing int pref.")
    exercise("if prefs.GetBoolean('browser', 'load-images') != 1:"
	     + "raise SystemError, 'browser:load-images Boolean should be 1'",
	     env, "Get an existing Boolean pref.")
    # A few value errors:
    exercise("x = prefs.Get('grail', 'Never:no:way:no:how!')", env,
	     "Ref to a non-existent pref.", KeyError)
    exercise("x = prefs.GetInt('landmarks', 'grail-home-page')", env,
	     "Typed ref to incorrect type.", TypeError)
    exercise("x = prefs.GetBoolean('browser', 'default-height')", env,
	     "Invalid Boolean (which has complicated err handling) typed ref.",
	     TypeError)
    # Editing:
    exercise("prefs.Set('browser', 'default-height', height + 1)", env,
	     "Set a simple value")
    exercise("if prefs.GetInt('browser', 'default-height') != height + 1:"
	     + "raise SystemError, 'Set of new height failed'", env,
	     "Get the new value.")
    # Saving: 
    exercise("if not prefs.Save(): raise SystemError", env,
	     "Save with new values (default-height).")
    

    print "GrailPrefs tests passed."

if __name__ == "__main__":

    global grail_root
    grail_root = '..'

    test()
