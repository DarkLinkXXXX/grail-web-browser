"""Assorted Tk-related subroutines used in Grail."""

# XXX test comment


import string
from types import *
from Tkinter import *


def make_text_box(parent, width=0, height=0, hbar=0, vbar=1):

    """Subroutine to create a text box.

    Create:
    - a both-ways filling and expanding frame, containing:
      - a text widget on the left, and
      - possibly a vertical scroll bar on the right.
      - possibly a horizonta; scroll bar at the bottom.

    Return the text widget and the frame widget.

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

    if hbar:
	hbar = Scrollbar(frame, orient=HORIZONTAL)
	hbar.pack(fill=X, side=BOTTOM)

    text = Text(frame, wrap=WORD)
    if width: text.config(width=width)
    if height: text.config(height=height)
    text.pack(expand=1, fill=BOTH, side=LEFT)

    if vbar:
	text['yscrollcommand'] = (vbar, 'set')
	vbar['command'] = (text, 'yview')

    if hbar:
	text['xscrollcommand'] = (hbar, 'set')
	hbar['command'] = (text, 'xview')

    text.vbar = vbar
    text.hbar = hbar

    return text, frame


def make_list_box(parent, width=0, height=0, hbar=0, vbar=1,
		  fill=BOTH, expand=1):

    """Subroutine to create a list box.

    Like make_text_box().

    """

    frame = Frame(parent)
    frame.pack(fill=BOTH, expand=1)

    if vbar:
	vbar = Scrollbar(frame)
	vbar.pack(fill=Y, side=RIGHT)

    if hbar:
	hbar = Scrollbar(frame, orient=HORIZONTAL)
	hbar.pack(fill=X, side=BOTTOM)

    listbox = Listbox(frame)
    if width: listbox.config(width=width)
    if height: listbox.config(height=height)
    listbox.pack(expand=expand, fill=fill, side=LEFT)

    if vbar:
	listbox['yscrollcommand'] = (vbar, 'set')
	vbar['command'] = (listbox, 'yview')

    if hbar:
	listbox['xscrollcommand'] = (hbar, 'set')
	hbar['command'] = (listbox, 'xview')

    return listbox, frame


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
