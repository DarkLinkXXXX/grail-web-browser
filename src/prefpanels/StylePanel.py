"""Grail style preferences panel."""

__version__ = "$Revision: 1.16 $"

# Base class for the panel:
import PrefsPanels

from Tkinter import *
import string


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
        f = Frame(frame)
        l = self.PrefsWidgetLabel(f, "Anchors:", label_width=20)
        cb = Checkbutton(f, text="Underline", borderwidth=1,
                         variable=v)
        cb.pack(side=LEFT)
        f.pack(fill=NONE, side=LEFT, pady='1m')
        self.RegisterUI('styles-common', 'history-ahist-underline',
                        'Boolean', v.get, v.set)
        self.RegisterUI('styles-common', 'history-atemp-underline',
                        'Boolean', v.get, v.set)
        self.RegisterUI('styles-common', 'history-a-underline',
                        'Boolean', v.get, v.set)

        frame.pack()
