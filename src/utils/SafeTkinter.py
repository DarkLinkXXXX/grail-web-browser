from types import *
# NB Don't import Tk!
from Tkinter import CallableTypes, TkVersion, TclVersion, TclError, \
     _cnfmerge, \
     Event, Variable, StringVar, IntVar, DoubleVar, BooleanVar, \
     mainloop, getint, getdouble, getboolean, \
     Misc, Wm, Pack, Place, Toplevel, \
     Button, Canvas, Checkbutton, \
     Entry, Frame, Label, Listbox, Menu, Menubutton, Message, Radiobutton, \
     Scale, Scrollbar, Text, Image, PhotoImage, BitmapImage, \
     OptionMenu, \
     image_names, image_types
from Tkconstants import *

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
