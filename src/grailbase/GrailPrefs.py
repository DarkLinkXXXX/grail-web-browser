"""Functional interface to Grail user preferences.

There are two preferences files.  The system-wide defaults file is located
in the grail root directory, and named "grail-defaults".  The user's custom
preferences is in the directory named by grailutil.getgraildir().  User
preference settings supercede the system defaults.

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

__version__ = "$Revision: 2.8 $"
# $Source: /home/john/Code/grail/src/grailbase/GrailPrefs.py,v $

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
    # a dict for new values, and a dict to track deletions (so user default
    # values duplicating system defaults can be excluded from save.

    def __init__(self, filename, readonly=0):
	"""Initiate from FILENAME with MODE (default 'r' read-only)."""
	self._filename = filename
	try:
	    f = open(filename)
	except IOError:
	    f = None
	self._new = {}
	self._deleted = {}
	if f:
	    self._last_mtime = os.stat(filename)[9]
	    self._db = rfc822.Message(f)
	    # Check for content misplaced after first blank line:
	    residue = string.strip(f.read())
	    if residue:
		sys.stderr.write("Ignoring preferences following blank line"
				 + " in %s\n" % f.name)
	    f.close()
	else:
	    self.file_mtime = 0
	    self._db = {}
	self._modified = 0

    def Get(self, group, prefnm):
	"""Get preference in GROUP with NAME, or raise KeyError if none."""
	key = make_key(group, prefnm)
	if self._new.has_key(key):
	    return self._new[key]
	else:
	    try:
		if not self._db:
		    raise KeyError
		else:
		    return self._db[key]
	    except KeyError:
		raise KeyError, "Preference %s not found" % ((group, prefnm),)

    def Set(self, group, prefnm, val):
	"""Set GROUP PREFERENCE to VALUE."""
	self._modified = 1
	k = make_key(group, prefnm)
	self._new[k] = str(val)
	if self._deleted.has_key(k):
	    # Undelete.
	    del self._deleted[k]

    def __delitem__(self, item):
	"""Register GROUP/PREFNAME so it won't be seen or saved."""
	self.Get(item[0], item[1])	# Validate existence of the item.
	self._deleted[make_key(item[0], item[1])] = 1


    def items(self):
	"""Return a list of ("group--prefnm", value) tuples."""
	got = []
	did = {}
	for k, v in self._db.items():
	    if self._deleted.has_key(k):
		continue
	    elif self._new.has_key(k):
		got.append((k, self._new[k]),)
		did[k] = 1
	    else:
		got.append((k, v,),)
	for k, v in self._new.items():
	    if not (did.has_key(k) or self._deleted.has_key(k)):
		got.append((k, v),)
	return got

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
	"""Write the preferences out to file, if possible."""
	try: os.rename(self._filename, self._filename + '.bak')
	except os.error: pass		# No file to backup.

	fp = open(self._filename, 'w')
	for k, v in self.items():
	    fp.write(k + ': ' + v + '\n')
	fp.close()
	self._modified = 0
	self._deleted = {}

class AllPreferences:
    """Maintain the combination of user and system preferences."""
    def __init__(self):
	self._user = Preferences(os.path.join(grailutil.getgraildir(),
					      USERPREFSFILENAME))
	from __main__ import grail_root
	self._sys = Preferences(os.path.join(grail_root,
					     SYSPREFSFILENAME),
				1)

    # Getting:

    def Get(self, group, prefnm, use_default=0):
	"""Get pref in GROUP with NAME, trying the user than the sys prefs.

	Optional SYS true means get system default value.

	Raise KeyError if not found."""
	if use_default:
	    return self._sys.Get(group, prefnm)
	else:
	    try:
		return self._user.Get(group, prefnm)
	    except KeyError:
		return self._sys.Get(group, prefnm)

    def _GetTyped(self, group, prefnm, cvrtr, type_name, use_default=0):
	"""Get preference, using CONVERTER to convert to type NAME.

	Optional SYS true means get system default value.

	Raise KeyError if not found, TypeError if value is wrong type."""
	val = self.Get(group, prefnm, use_default)
	try:
	    return cvrtr(val)
	except ValueError:
	    raise TypeError, ('%s not %s: %s'
			       % (str((group, prefnm)), type_name, `val`))

    def GetInt(self, group, prefnm, use_default=0):
	return self._GetTyped(group, prefnm, string.atoi, "integer",
			      use_default)
    def GetFloat(self, group, prefnm, use_default=0):
	return self._GetTyped(group, prefnm, string.atof, "float",
			      use_default)
    def GetBoolean(self, group, prefnm, use_default=0):
	got = self._GetTyped(group, prefnm, string.atoi, "Boolean",
			     use_default)
	if got not in (0, 1):
	    raise TypeError, ('%s not %s: %s'
			      % ((group, prefnm), "Boolean", `got`))
	return got

    # Editing:

    def Set(self, group, prefnm, val):
	"""Assign GROUP PREFERENCE with VALUE."""
	self._user.Set(group, prefnm, val)

    def Editable(self):
	"""Identify or establish user's prefs file, or IO error."""
	return self._user.Editable()

    def Tampered(self):
	"""True if user prefs file modified since we read them."""
	return self._user.Tampered()

    def NeedsSave(self): return self._user.NeedsSave()

    def Save(self):
	"""Save (only) values different than sys defaults in the users file."""
	if not self._user.Editable():
	    raise IOError, 'Unable to get user prefs ' + self._user._filename
	for prefkey, val in self._user.items():
	    # Cull user preferences with same value as system default:
	    k = split_key(prefkey)
	    if len(k) == 1:
		# Probably a comment - we don't retain users' comments unless
		# they make them look like distinct group--prefnm values.
		continue
	    else:
		try:
		    if self._sys.Get(k[0], k[1]) == val:
			del self._user[(k[0], k[1])]
		except KeyError:
		    # User file absent in system defaults - tolerate it.
		    continue
	self._user.Save()

def make_key(group, prefnm):
    """Produce a key from preference GROUP and NAME strings."""
    return string.lower(group + '--' + prefnm)
def split_key(key):
    """Produce a key from preference GROUP and NAME strings."""
    return string.split(key, '--')
		    
def test():
    """Exercise preferences mechanisms."""
    sys.path.insert(0, "../utils")
    from testing import exercise
    
    env = sys.modules[__name__].__dict__

    # Reading the db:
    exercise("prefs = AllPreferences()", env, "Suck in the prefs")

    # Getting values:
    exercise("origin = prefs.Get('landmarks', 'grail-home-page')", env,
	     "Get an existing plain prefnm.")
    exercise("origheight = prefs.GetInt('browser', 'default-height')", env,
	     "Get an existing int prefnm.")
    exercise("if prefs.GetBoolean('browser', 'load-images') != 1:"
	     + "raise SystemError, 'browser:load-images Boolean should be 1'",
	     env, "Get an existing Boolean prefnm.")
    # A few value errors:
    exercise("x = prefs.Get('grail', 'Never:no:way:no:how!')", env,
	     "Ref to a non-existent prefnm.", KeyError)
    exercise("x = prefs.GetInt('landmarks', 'grail-home-page')", env,
	     "Typed ref to incorrect type.", TypeError)
    exercise("x = prefs.GetBoolean('browser', 'default-height')", env,
	     "Invalid Boolean (which has complicated err handling) typed ref.",
	     TypeError)
    # Editing:
    exercise("prefs.Set('browser', 'default-height', origheight + 1)", env,
	     "Set a simple value")
    exercise("if prefs.GetInt('browser', 'default-height') != origheight + 1:"
	     + "raise SystemError, 'Set of new height failed'", env,
	     "Get the new value.")

    exercise("prefs.Set('browser', 'default-height', origheight)", env,
	     "Set a simple value")

    # Saving - should just rewrite existing user prefs file, sans comments
    # and any lines duplicating system prefs.
    exercise("prefs.Save()", env, "Save as it was originally.")
    

    print "GrailPrefs tests passed."

if __name__ == "__main__":

    global grail_root
    grail_root = '..'

    test()
