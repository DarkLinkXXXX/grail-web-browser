from types import *
# NB Don't import Tk!
from Tkinter import CallableTypes, TkVersion, TclVersion, \
     _cnfmerge, \
     Event, Variable, StringVar, IntVar, DoubleVar, BooleanVar, \
     mainloop, getint, getdouble, getboolean, \
     Misc, Wm, Pack, Place, Toplevel, \
     Button, Canvas, Checkbutton, \
     Entry, Frame, Label, Menu, Menubutton, Message, Radiobutton, \
     Scale, Scrollbar, Text, Image, PhotoImage, BitmapImage, \
     image_names, image_types

def _castrate(tk):
    """Remove all Tcl commands that can affect the file system."""
    def rm(name, tk=tk):
	tk.call('rename', name, '')
    rm('exec')
    rm('cd')
    rm('open')
    rm('send')
