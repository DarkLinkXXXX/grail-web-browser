"""Grail style preferences panel."""

__version__ = "$Revision: 1.17 $"

# Base class for the panel:
import PrefsPanels

from Tkinter import *
import string


class ColorButton(Button):
    def __init__(self, master, cnf={}, **kw):
        kw["text"] = "Set"              # don't allow these to be provided
        #kw["font"] = "tiny"
        kw["background"] = kw.get("foreground")
        kw["highlightthickness"] = 0
        kw["command"] = self.__ask_color
        kw["cnf"] = cnf
        self.__master = master
        apply(Button.__init__, (self, master), kw)

    def get(self):
        return self.cget("foreground")

    def set(self, color):
        self.configure(foreground=color, background=color)

    def __ask_color(self):
        from pynche.pyColorChooser import askcolor
        rgb, name = askcolor(self.get(), master=self.__master)
        if rgb:
            self.set("#%02x%02x%02x" % rgb)


class StylePanel(PrefsPanels.Framework):
    """Panel for selecting viewer presentation styles."""

    HELP_URL = "help/prefs/styles.html"

    def CreateLayout(self, name, frame):

        style_sizes = string.split(self.app.prefs.Get('styles',
                                                      'all-sizes'))
        style_families = string.split(self.app.prefs.Get('styles',
                                                         'all-families'))

        self.PrefsRadioButtons(frame, "Font size group:", style_sizes,
                               'styles', 'size', label_width=20)
        self.PrefsRadioButtons(frame, "Font Family:", style_families,
                               'styles', 'family', label_width=20)
        # Anchors:

        v = StringVar(frame)
        vhover = StringVar(frame)
        f = Frame(frame)
        l = self.PrefsWidgetLabel(f, "Anchors:", label_width=20)
        cb = Checkbutton(f, text="Underline", borderwidth=1,
                         variable=v)
        cb.pack(side=LEFT)
        cb = Checkbutton(f, text="Underline when Hovering", borderwidth=1,
                         variable=vhover)
        cb.pack(side=LEFT)
        f.pack(fill=NONE, pady='1m', anchor=W)
        self.RegisterUI('styles-common', 'history-ahist-underline',
                        'Boolean', v.get, v.set)
        self.RegisterUI('styles-common', 'history-atemp-underline',
                        'Boolean', vhover.get, vhover.set)
        self.RegisterUI('styles-common', 'history-a-underline',
                        'Boolean', v.get, v.set)
        self.RegisterUI('styles-common', 'history-hover-underline',
                        'Boolean', vhover.get, vhover.set)

        # Anchor colors:

        f = Frame(frame)
        l = self.PrefsWidgetLabel(f, "", label_width=20)
        f1 = Frame(f)
        f1.pack(side=LEFT, expand=1, fill=X)
        f2 = Frame(f)
        f2.pack(side=LEFT, expand=1, fill=X)
        self.__add_color(f1, 'history-a-foreground',
                         "Anchor color")
        Frame(f1, height=6).pack()
        self.__add_color(f1, 'history-ahist-foreground',
                         "Visited anchor color")
        self.__add_color(f2, 'history-atemp-foreground',
                         "Active anchor color")
        Frame(f2, height=6).pack()
        self.__add_color(f2, 'history-hover-foreground',
                         "Hover color")
        f.pack(fill=X, pady='1m', anchor=W)

        frame.pack()

    def __add_color(self, frame, prefname, description):
        f = Frame(frame)
        button = ColorButton(f)
        button.pack(side=LEFT)
        self.RegisterUI('styles-common', prefname, 'string',
                        button.get, button.set)
        Label(f, text=" " + description).pack(side=LEFT)
        f.pack(anchor=W)
        return button
