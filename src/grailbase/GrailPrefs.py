"""Functional interface to Grail user preferences.

See the Grail htdocs/info/extending/preferences.html for documentation."""

# Todo:
#  - Preference-change callback funcs

__version__ = "$Revision: 2.15 $"
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

    # We maintain an rfc822 snapshot of the file, which we read only once
    # and dicts for:
    #  - ._new: new settings not yet saved
    #  - ._established: new settings saved and referenced read-in settings
    #  - ._deleted: deleted settings, so user default values duplicating
    #               system defaults can be excluded from save.

    def __init__(self, filename, readonly=0):
	"""Initiate from FILENAME with MODE (default 'r' read-only)."""
	self._filename = filename
	try:
	    f = open(filename)
	except IOError:
	    f = None
	self._rfc822 = None			# Settings read in from file.
	self._new = {}			# Settings not read in, not yet saved.
	self._established = {}		# Settings referenced and saved.
	self._deleted = {}		# Settings overridden, not yet saved.
	if f:
	    self._last_mtime = os.stat(filename)[9]
	    self._rfc822 = rfc822.Message(f)
	    # Check for content misplaced after first blank line:
	    residue = string.strip(f.read())
	    if residue:
		sys.stderr.write("Ignoring preferences following blank line"
				 + " in %s\n" % f.name)
	    for k, v in self._rfc822.items():
		# _established dict is much faster than _rfc822 object -
		# bite the bullet and transfer at the beginning:
		self._established[k] = v
	    f.close()
	else:
	    self.file_mtime = 0
	self._modified = 0

    def Get(self, group, component):
	"""Get preference GROUP, COMPONENT, or raise KeyError if none."""
	key = make_key(group, component)
	if self._new.has_key(key):
	    return self._new[key]
	elif self._established.has_key(key):
	    return self._established[key]
	else:
	    raise KeyError, "Preference %s not found" % ((group,
							  component),)

    def Set(self, group, component, val):
	"""Set preference GROUP, COMPONENT to VALUE."""
	self._modified = 1
	k = make_key(group, component)
	self._new[k] = str(val)
	if self._established.has_key(k):
	    # Override established val, ensure save doesn't save both:
	    del self._established[k]
	if self._deleted.has_key(k):
	    # Undelete.
	    del self._deleted[k]

    def __delitem__(self, item):
	"""Inhibit preference (GROUP, COMPONENT) from being seen or saved."""
	self.Get(item[0], item[1])	# Validate existence of the item.
	self._deleted[make_key(item[0], item[1])] = 1


    def items(self):
	"""Return a list of ("group--component", value) tuples."""
	got = []
	did = {}
	for k, v in self._established.items() + self._new.items():
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

    def Save(self):
	"""Write the preferences out to file, if possible."""
	try: os.rename(self._filename, self._filename + '.bak')
	except os.error: pass		# No file to backup.

	fp = open(self._filename, 'w')
	for k, v in self.items():
	    fp.write(k + ': ' + v + '\n')
	fp.close()
	# Pour new items into established, now that they're saved:
	for k, v in self._new.items():
	    self._established[k] = v
	# ... and reinit new:
	self._new = {}
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
	self._callbacks = {}

    def AddGroupCallback(self, group, callback):
	"""Register FUNC to invok when saving changed prefs in GROUP."""
	if self._callbacks.has_key(group):
	    if callback not in self._callbacks[group]:
		self._callbacks[group].append(callback)
	else:
	    self._callbacks[group] = [callback]

    # Getting:

    def Get(self, group, component, use_default=0):
	"""Get pref GROUP, COMPONENT, trying the user then the sys prefs.

	Optional USE_DEFAULT true means get system default ("factory") value.

	Raise KeyError if not found."""
	if use_default:
	    return self._sys.Get(group, component)
	else:
	    try:
		return self._user.Get(group, component)
	    except KeyError:
		return self._sys.Get(group, component)

    def GetTyped(self, group, component, type_name, use_default=0):
	"""Get preference, using CONVERTER to convert to type NAME.

	Optional SYS true means get system default value.

	Raise KeyError if not found, TypeError if value is wrong type."""
	val = self.Get(group, component, use_default)
	try:
	    return typify(val, type_name)
	except TypeError:
	    raise TypeError, ('%s should be %s: %s'
			       % (str((group, component)), type_name, `val`))

    def GetInt(self, group, component, use_default=0):
	return self.GetTyped(group, component, "int", use_default)
    def GetFloat(self, group, component, use_default=0):
	return self.GetTyped(group, component, "float", use_default)
    def GetBoolean(self, group, component, use_default=0):
	return self.GetTyped(group, component, "Boolean", use_default)

    def GetGroup(self, group):
	"""Get a list of ((group,component), value) tuples in group."""
	got = []
	prefix = string.lower(group) + '--'
	l = len(prefix)
	for it in self.items():
	    if prefix == it[0][:l]:
		got.append((split_key(it[0]), it[1]))
	return got

    def items(self):
	got = {}
	for it in self._sys.items():
	    got[it[0]] = it[1]
	for it in self._user.items():
	    got[it[0]] = it[1]
	return got.items()

    # Editing:

    def Set(self, group, component, val):
	"""Assign GROUP PREFERENCE with VALUE."""
	if self.Get(group, component) != val:
	    self._user.Set(group, component, val)

    def Editable(self):
	"""Identify or establish user's prefs file, or IO error."""
	return self._user.Editable()

    def Tampered(self):
	"""True if user prefs file modified since we read them."""
	return self._user.Tampered()

    def Save(self):
	"""Save (only) values different than sys defaults in the users file."""
	if not self._user.Editable():
	    raise IOError, 'Unable to get user prefs ' + self._user._filename
	# Process the callbacks:
	did_groups = {}
	for prefkey, val in self._user._new.items():
	    [group, component] = split_key(prefkey)
	    if not did_groups.has_key(group):
		did_groups[group] = 1
		if self._callbacks.has_key(group):
		    for callback in self._callbacks[group]:
			apply(callback, ())
	for prefkey, val in self._user.items():
	    # Cull user preferences with same value as system default:
	    k = split_key(prefkey)
	    if len(k) == 1:
		# Aberrant entries (probly comments) are not retained.
		continue
	    else:
		# Discard items that duplicate settings in sys defaults:
		try:
		    if self._sys.Get(k[0], k[1]) == val:
			del self._user[(k[0], k[1])]
		except KeyError:
		    # User's file pref absent from system defaults file - ok.
		    continue
	self._user.Save()


def make_key(group, component):
    """Produce a key from preference GROUP, COMPONENT strings."""
    return string.lower(group + '--' + component)
def split_key(key):
    """Produce a key from preference GROUP, COMPONENT strings."""
    return string.split(key, '--')
		    

def typify(val, type_name):
    """Convert string value to specific type, or raise type err if impossible.

    Type is one of 'string', 'int', 'float', or 'Boolean' (note caps)."""
    try:
	if type_name == 'string':
	    return val
	elif type_name == 'int':
	    return string.atoi(val)
	elif type_name == 'float':
	    return string.atof(val)
	elif type_name == 'Boolean':
	    i = string.atoi(val)
	    if i not in (0, 1):
		raise TypeError, '%s should be Boolean' % `val`
	    return i
    except ValueError:
	    raise TypeError, '%s should be %s' % (`val`, type_name)
    
    raise ValueError, ('%s not supported - must be one of %s'
		       % (`type_name`, ['string', 'int', 'float', 'Boolean']))
    

def test():
    """Exercise preferences mechanisms."""
    sys.path.insert(0, "../utils")
    from testing import exercise
    
    env = sys.modules[__name__].__dict__

    # Reading the db:
    exercise("prefs = AllPreferences()", env, "Suck in the prefs")

    # Getting values:
    exercise("origin = prefs.Get('landmarks', 'grail-home-page')", env,
	     "Get an existing plain component.")
    exercise("origheight = prefs.GetInt('browser', 'default-height')", env,
	     "Get an existing int component.")
    exercise("if prefs.GetBoolean('browser', 'load-images') != 1:"
	     + "raise SystemError, 'browser:load-images Boolean should be 1'",
	     env, "Get an existing Boolean component.")
    # A few value errors:
    exercise("x = prefs.Get('grail', 'Never:no:way:no:how!')", env,
	     "Ref to a non-existent component.", KeyError)
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
    

    return prefs
    print "GrailPrefs tests passed."

if __name__ == "__main__":

    global grail_root
    grail_root = '..'

    prefs = test()
