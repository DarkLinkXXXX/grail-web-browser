from types import *
# NB Don't import Tk!
from Tkinter import TkVersion, TclVersion, TclError, \
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

from Tkinter import tkinter

class _DumbTkinter:
    """Helper class to provide interfaces to low-level handler functions"""
    READABLE = 1
    WRITABLE = 2
    createfilehandler = tkinter.createfilehandler
    deletefilehandler = tkinter.deletefilehandler
    createtimerhandler = tkinter.createtimerhandler

tkinter = _DumbTkinter()

def _castrate(tk):
    """Remove all Tcl commands that can affect the file system."""
    if not hasattr(tk, 'eval'): return # For Rivet
    def rm(name, tk=tk):
	tk.call('rename', name, '')
    # Make sure the menu support commands are autoloaded, since we need them
    tk.eval("auto_load tkMenuInvoke")
    rm('exec')
    rm('cd')
    rm('open') # This is what breaks the menu support commands
    rm('send')
