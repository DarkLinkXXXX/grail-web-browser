from types import *
# NB Don't import Tk!
from Tkinter import CallableTypes, TkVersion, TclVersion, \
     _cnfmerge, \
     Event, Variable, StringVar, IntVar, DoubleVar, BooleanVar, \
     mainloop, getint, getdouble, getboolean, \
     Misc, Wm, Pack, Place, Toplevel, \
     Button, Canvas, Checkbutton, \
     Entry, Frame, Label, Listbox, Menu, Menubutton, Message, Radiobutton, \
     Scale, Scrollbar, Text, Image, PhotoImage, BitmapImage, \
     image_names, image_types

# Symbolic constants (easier copied than included)

# Booleans
NO=FALSE=OFF=0
YES=TRUE=ON=1

# -anchor
N='n'
S='s'
W='w'
E='e'
NW='nw'
SW='sw'
NE='ne'
SE='se'
CENTER='center'

# -fill
NONE='none'
X='x'
Y='y'
BOTH='both'

# -side
LEFT='left'
TOP='top'
RIGHT='right'
BOTTOM='bottom'

# -relief
RAISED='raised'
SUNKEN='sunken'
FLAT='flat'
RIDGE='ridge'
GROOVE='groove'

# -orient
HORIZONTAL='horizontal'
VERTICAL='vertical'

# -tabs
NUMERIC='numeric'

# -wrap
CHAR='char'
WORD='word'

# -align
BASELINE='baseline'

# Special tags, marks and insert positions
SEL='sel'
SEL_FIRST='sel.first'
SEL_LAST='sel.last'
END='end'
INSERT='insert'
CURRENT='current'
ANCHOR='anchor'

def _castrate(tk):
    """Remove all Tcl commands that can affect the file system."""
    def rm(name, tk=tk):
	tk.call('rename', name, '')
    # Make sure the menu support commands are autoloaded, since we need them
    tk.eval("auto_load tkMenuInvoke")
    rm('exec')
    rm('cd')
    rm('open') # This is what breaks the menu support commands
    rm('send')
