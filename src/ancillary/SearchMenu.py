"""Search menu extension for Grail."""

from Tkinter import *
import tktools

class SearchMenu:

    def __init__(self, menu):
	self.browser = menu.grail_browser
	menu.add('command',
		 label='Find...',
		 command=self.find_command)
	menu.add('command',
		 label='Find again',
		 command=self.find_again_command)
	self.sdialog = None

    def find_command(self):
	self.create_dialog(1)

    def find_again_command(self):
	self.create_dialog(0)
	self.sdialog.search_command()

    def create_dialog(self, force=0):
	if not self.sdialog:
	    self.sdialog = SearchDialog(self.browser)
	elif force:
	    self.sdialog.root.deiconify()
	    self.sdialog.pat_entry.focus_set()
	    self.sdialog.pat_entry.select_range(0, END)


class SearchDialog:

    def __init__(self, browser):
	self.browser = browser
	self.root = Toplevel(browser.root)
	self.root.title("Search dialog")
	self.create_widgets()

    def create_widgets(self):
	self.pat_entry, self.pat_frame = tktools.make_form_entry(
	    self.root, "Find string:")
	self.pat_entry['exportselection'] = 0
	self.pat_entry.bind('<Return>', self.return_event)
	self.pat_entry.focus_set()

	self.mid_frame = Frame(self.root)
	self.mid_frame.pack(fill=X)

	self.regexp_var = BooleanVar()
	self.case_var = BooleanVar()
	self.backwards_var = BooleanVar()

	self.regexp_checkbutton = Checkbutton(self.mid_frame,
					      text="regexp",
					      variable=self.regexp_var)
	self.regexp_checkbutton.pack(side=LEFT)
	self.case_checkbutton = Checkbutton(self.mid_frame,
					    text="case sensitive",
					    variable=self.case_var)
	self.case_checkbutton.pack(side=LEFT, expand=1)
	self.backwards_checkbutton = Checkbutton(self.mid_frame,
						 text="backwards",
						 variable=self.backwards_var)
	self.backwards_checkbutton.pack(side=RIGHT)

	self.bot_frame = Frame(self.root)
	self.bot_frame.pack(fill=X)

	self.search_button = Button(self.bot_frame, text="Search",
				    command=self.search_command)
	self.search_button.pack(side=LEFT)
	self.search_close_button = Button(self.bot_frame, text="Search+Close",
					  command=self.search_close_command)
	self.search_close_button.pack(side=LEFT, expand=1) # Center
	self.close_button = Button(self.bot_frame, text="Close",
				   command=self.close_command)
	self.close_button.pack(side=RIGHT)

    def return_event(self, event):
	self.search()

    def search_command(self):
	self.search()

    def search_close_command(self):
	if not self.search():
	    return
	self.close_command()

    def close_command(self):
	self.root.withdraw()

    def search(self):
	text = self.browser.viewer.text
	try:
	    index = text.index(SEL_FIRST)
	    index = "%s + 1 chars" % str(index)
	except TclError:
	    index = "1.0"
	pat = self.pat_entry.get()
	if not pat:
	    self.root.bell()
	    return 0
	length = IntVar()
	hit = text.search(pat, index, count=length,
			  nocase=not self.case_var.get(),
			  regexp=self.regexp_var.get(),
			  backwards=self.backwards_var.get())
	if not hit:
	    self.root.bell()
	    return 0
	try:
	    text.tag_remove(SEL, SEL_FIRST, SEL_LAST)
	except TclError:
	    pass
	text.tag_add(SEL, hit, "%s + %s chars" % (hit, length.get()))
	text.yview_pickplace(SEL_FIRST)
	return 1
