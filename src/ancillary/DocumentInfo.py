"""Simple 'Document Info...' dialog for Grail."""

__version__ = '$Revision: 2.4 $'
#  $Source: /home/john/Code/grail/src/ancillary/DocumentInfo.py,v $

import string
import Tkinter
import tktools
import urlparse

FIELD_BREAKER = string.maketrans("&", "\n")
MAX_TEXT_FIELD_LINES = 10


class DocumentInfoDialog(Tkinter.Toplevel):
    def __init__(self, master, context, *args, **kw):
	if not kw.has_key("class_"):
	    kw["class_"] = "DocumentInfo"
	apply(Tkinter.Toplevel.__init__, (self, master) + args, kw)
	self.iconname("Document Info")
	page_title = context.page.title()
	self.title("Document Info"
		   + (page_title and (": " + page_title) or ""))
	self.bind("<Alt-W>", self.__destroy)
	self.bind("<Alt-w>", self.__destroy)
	self.bind("<Return>", self.__destroy)
	self.protocol("WM_DELETE_WINDOW", self.__destroy)
	frame, self.__topfr, botfr = tktools.make_double_frame(self)
	#
	# Info display
	#
	url = context.page.url()
	scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
	url = urlparse.urlunparse((scheme, netloc, path, '', '', ''))
	self.add_label_field("Title", page_title or "(unknown)", "title")
	self.add_label_field("URI", url, "uri")
	if fragment:
	    self.add_label_field("Fragment", fragment, "fragment")
	headers = context.get_headers()
	if headers.has_key("date") and type(headers["date"]) is type(self):
	    self.add_label_field("", "(Loaded from local cache.)", "cached")
	items = headers.items()
	items.sort()
	s = ""
	for k, v in items:
	    if k == 'date' and type(v) is type(self):
		import ht_time
		v = ht_time.unparse(v.get_secs())
	    s = "%s%s:\t%s\n" % (s, k, v)
	self.add_text_field("Response headers", s, "headers")
	if query:
	    query = string.translate(query, FIELD_BREAKER)
	    self.add_text_field("Query fields", query, "query")
	postdata = context.get_postdata()
	if postdata:
	    postdata = string.translate(postdata, FIELD_BREAKER)
	    self.add_text_field("POST fields", postdata, "postdata")
	#
	# Bottom button
	#
	fr = Tkinter.Frame(botfr, borderwidth=1, relief=Tkinter.SUNKEN)
	fr.pack()
	btn = Tkinter.Button(fr, text="OK", command=self.__destroy)
	# '2m' is the value from the standard Tk 'tk_dialog' command
	btn.pack(padx='2m', pady='2m')
	btn.focus_set()

    def add_field(self, label, name):
	fr = Tkinter.Frame(self.__topfr, name=name)
	fr.pack(expand=1, fill=Tkinter.X)
	if label: label = label + ": "
	Tkinter.Label(fr, text=label, width=17, anchor=Tkinter.E, name="label"
		      ).pack(anchor=Tkinter.NE, side=Tkinter.LEFT)
	return fr

    def add_label_field(self, label, value, name):
	fr = self.add_field(label, name)
	label = Tkinter.Label(fr, text=value, anchor=Tkinter.W, name="value")
	label.pack(anchor=Tkinter.W, fill=Tkinter.X, expand=1)
	return label

    def add_text_field(self, label, value, name):
	fr = self.add_field(label, name)
	if value and value[-1] != "\n":
	    value = value + "\n"
	text, frame = tktools.make_text_box(
	    fr, takefocus=0, width=60, vbar=1,
	    height=min(MAX_TEXT_FIELD_LINES, 1 + map(None, value).count("\n")))
	frame.pack(side=Tkinter.LEFT)
	text.insert(Tkinter.END, value)
	text["state"] = Tkinter.DISABLED
	return text

    def __destroy(self, event=None):
	self.destroy()
	return "break"


class DocumentInfoCommand:
    def __init__(self, obj):
	try:
	    self.__viewer = obj.viewer
	except AttributeError:
	    self.__viewer = obj

    def __call__(self, event=None):
	DocumentInfoDialog(self.__viewer.master,
			   self.__viewer.context)

#
#  end of file
