"""Assorted Tk-related subroutines used in Grail."""


import string
from types import *
from Tkinter import *


# Default dimensions for text box
TEXT_WIDTH = 60
TEXT_HEIGHT = 16


def make_text_box(parent, width=TEXT_WIDTH, height=TEXT_HEIGHT):

    """Subroutine to create a text box.

    Create:
    - a both-ways filling and expanding frame, containing:
      - a text widget on the left, and
      - a vertical scroll bar on the right.

    Return the text widget and the frame widget.

    """

    frame = Frame(parent)
    frame.pack(fill='both', expand=1)

    vbar = Scrollbar(frame)
    vbar.pack(fill='y', side='right')

    text = Text(frame, wrap='word')
    if width: text.config(width=width)
    if height: text.config(height=height)
    text.pack(expand=1, fill='both', side='left')

    text['yscrollcommand'] = (vbar, 'set')
    vbar['command'] = (text, 'yview')

    return text, frame


def make_form_entry(parent, label):

    """Subroutine to create a form entry.

    Create:
    - a horizontally filling and expanding frame, containing:
      - a label on the left, and
      - a text entry on the right.

    Return the entry widget and the frame widget.

    """

    frame = Frame(parent)
    frame.pack(fill='x')

    label = Label(frame, text=label)
    label.pack(side='left')

    entry = Entry(frame, relief='sunken', border= 2)
    entry.pack(side='left', fill='x', expand=1)

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
    entry.insert('end', flatten(sys.argv))
    root.mainloop()


if __name__ == '__main__':
    test()
