# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""Printing interface for HTML documents."""

import printing.PSParser

parse = printing.PSParser.PrintingHTMLParser


def add_options(dialog, settings, top):
    from Tkinter import X
    import tktools
    htmlfr = tktools.make_group_frame(top, "html", "HTML options:", fill=X)
    #  Image printing controls:
    dialog.__imgchecked = dialog.new_checkbox(
	htmlfr, "Print images", settings.imageflag)
    dialog.__greychecked = dialog.new_checkbox(
	htmlfr, "Reduce images to greyscale", settings.greyscale)
    #  Anchor-handling selections:
    dialog.__footnotechecked = dialog.new_checkbox(
	htmlfr, "Footnotes for anchors", settings.footnoteflag)
    dialog.__underchecked = dialog.new_checkbox(
	htmlfr, "Underline anchors", settings.underflag)


def update_settings(dialog, settings):
    settings.footnoteflag = dialog.__footnotechecked.get()
    settings.greyscale = dialog.__greychecked.get()
    settings.imageflag = dialog.__imgchecked.get()
    settings.underflag = dialog.__underchecked.get()
