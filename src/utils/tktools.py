"""Assorted Tk-related subroutines used in Grail."""


import string
from types import *
from Tkinter import *

def _clear_entry_widget(event):
    try:
	widget = event.widget
	widget.delete(0, INSERT)
    except: pass
def install_keybindings(root):
    root.bind_class('Entry', '<Control-u>', _clear_entry_widget)


def make_toplevel(master, title=None, class_=None):
    """Create a Toplevel widget.

    This is a shortcut for a Toplevel() instantiation plus calls to
    set the title and icon name of the widget.

    """

    if class_:
	widget = Toplevel(master, class_=class_)
    else:
	widget = Toplevel(master)
    if title:
	widget.title(title)
	widget.iconname(title)
    return widget

def set_transient(widget, master, relx=0.5, rely=0.3):
    """Make an existing toplevel widget transient for a master.

    The widget must exist but should not yet have been placed; in
    other words, this should be called after creating all the
    subwidget but before letting the user interact.
    """

    widget.withdraw() # Remain invisible while we figure out the geometry
    widget.transient(master)
    widget.update_idletasks() # Actualize geometry information
    m_width = master.winfo_width()
    m_height = master.winfo_height()
    w_width = widget.winfo_reqwidth()
    w_height = widget.winfo_reqheight()
    m_x = master.winfo_rootx()
    m_y = master.winfo_rooty()
    x = m_x + (m_width - w_width) * relx
    y = m_y + (m_height - w_height) * rely
    widget.geometry("+%d+%d" % (x, y))
    widget.deiconify() # Become visible at the desired location
    return widget


def make_scrollbars(parent, hbar, vbar):

    """Subroutine to create a frame with scrollbars.

    This is used by make_text_box and similar routines.

    Note: the caller is responsible for setting the x/y scroll command
    properties (e.g. by calling set_scroll_commands()).

    Return a triple containing the hbar, the vbar, and the frame,
    where hbar and vbar are None if not requested.

    """

    frame = Frame(parent)
    frame.pack(fill=BOTH, expand=1)

    if vbar:
	if not hbar:
	    vbar = Scrollbar(frame)
	    vbar.pack(fill=Y, side=RIGHT)
	else:
	    vbarframe = Frame(frame, borderwidth=0)
	    vbarframe.pack(fill=Y, side=RIGHT)
	    vbar = Scrollbar(vbarframe)
	    vbar.pack(expand=1, fill=Y, side=TOP)
	    sbwidth = vbar.winfo_reqwidth()
	    corner = Frame(vbarframe, width=sbwidth, height=sbwidth)
	    corner.pack(side=BOTTOM)
    else:
	vbar = None

    if hbar:
	hbar = Scrollbar(frame, orient=HORIZONTAL)
	hbar.pack(fill=X, side=BOTTOM)
    else:
	hbar = None

    return hbar, vbar, frame


def set_scroll_commands(widget, hbar, vbar):

    """Link a scrollable widget to its scroll bars.

    The scroll bars may be empty.

    """

    if vbar:
	widget['yscrollcommand'] = (vbar, 'set')
	vbar['command'] = (widget, 'yview')

    if hbar:
	widget['xscrollcommand'] = (hbar, 'set')
	hbar['command'] = (widget, 'xview')

    widget.vbar = vbar
    widget.hbar = hbar


def make_text_box(parent, width=0, height=0, hbar=0, vbar=1,
		  fill=BOTH, expand=1, wrap=WORD):

    """Subroutine to create a text box.

    Create:
    - a both-ways filling and expanding frame, containing:
      - a text widget on the left, and
      - possibly a vertical scroll bar on the right.
      - possibly a horizonta; scroll bar at the bottom.

    Return the text widget and the frame widget.

    """

    hbar, vbar, frame = make_scrollbars(parent, hbar, vbar)

    widget = Text(frame, wrap=wrap)
    if width: widget.config(width=width)
    if height: widget.config(height=height)
    widget.pack(expand=expand, fill=fill, side=LEFT)

    set_scroll_commands(widget, hbar, vbar)

    return widget, frame


def make_list_box(parent, width=0, height=0, hbar=0, vbar=1,
		  fill=BOTH, expand=1):

    """Subroutine to create a list box.

    Like make_text_box().

    """

    hbar, vbar, frame = make_scrollbars(parent, hbar, vbar)

    widget = Listbox(frame)
    if width: widget.config(width=width)
    if height: widget.config(height=height)
    widget.pack(expand=expand, fill=fill, side=LEFT)

    set_scroll_commands(widget, hbar, vbar)

    return widget, frame


def make_canvas(parent, width=0, height=0, hbar=1, vbar=1,
		  fill=BOTH, expand=1):

    """Subroutine to create a canvas.

    Like make_text_box().

    """

    hbar, vbar, frame = make_scrollbars(parent, hbar, vbar)

    widget = Canvas(frame, scrollregion=(0, 0, width, height))
    if width: widget.config(width=width)
    if height: widget.config(height=height)
    widget.pack(expand=expand, fill=fill, side=LEFT)

    set_scroll_commands(widget, hbar, vbar)

    return widget, frame



def make_form_entry(parent, label):

    """Subroutine to create a form entry.

    Create:
    - a horizontally filling and expanding frame, containing:
      - a label on the left, and
      - a text entry on the right.

    Return the entry widget and the frame widget.

    """

    frame = Frame(parent)
    frame.pack(fill=X)

    label = Label(frame, text=label)
    label.pack(side=LEFT)

    entry = Entry(frame, relief=SUNKEN, border= 2)
    entry.pack(side=LEFT, fill=X, expand=1)

    return entry, frame

# This is a slightly modified version of the function above.  This
# version does the proper alighnment of labels with their fields.  It
# should probably eventually replace make_form_entry altogether.
#
# The one annoying bug is that the text entry field should be
# expandable while still aligning the colons.  This doesn't work yet.
#
def make_labeled_form_entry(parent, label, entrywidth=20, entryheight=1):
    """Subroutine to create a form entry.

    Create:
    - a horizontally filling and expanding frame, containing:
      - a label on the left, and
      - a text entry on the right.

    Return the entry widget and the frame widget.
    """
    if label[-1] != ':': label = label + ':'

    frame = Frame(parent)
    frame.pack(fill='x')

    if entryheight == 1:
	entry = Entry(frame, relief='sunken', border= 2, width=entrywidth)
	entry.pack(side='right', fill='x')
	label = Label(frame, text=label)
	label.pack(side='right')
    else:
	label = Label(frame, text=label)
	label.pack(side='left')
	entry = make_text_box(frame, entrywidth, entryheight, 1, 1)

    return entry, frame, label



def flatten(msg):
    """Turn a list or tuple into a single string -- recursively."""
    t = type(msg)
    if t in (ListType, TupleType):
	msg = string.join(map(flatten, msg))
    elif t is ClassType:
	msg = msg.__name__
    else:
	msg = str(msg)
    return msg


def boolean(s):
    """Test whether a string is a Tk boolean, without error checking."""
    if string.lower(s) in ('', '0', 'no', 'off', 'false'): return 0
    else: return 1


def test():
    """Test make_text_box(), make_form_entry(), flatten(), boolean()."""
    import sys
    root = Tk()
    entry, eframe = make_form_entry(root, 'Boolean:')
    text, tframe = make_text_box(root)
    def enter(event, entry=entry, text=text):
	s = boolean(entry.get()) and '\nyes' or '\nno'
	text.insert('end', s)
    entry.bind('<Return>', enter)
    entry.insert(END, flatten(sys.argv))
    root.mainloop()


if __name__ == '__main__':
    test()
