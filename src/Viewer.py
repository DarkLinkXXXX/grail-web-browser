"""Viewer class.
"""

from Tkinter import *
import tktools
import formatter
import string
from Context import Context
from Cursors import *
from types import StringType
from urlparse import urljoin
from DefaultStylesheet import DefaultStylesheet


DINGBAT_FONT = None
SYMBOL_FONT = None
MIN_IMAGE_LEADER = "\240"		# Non-breaking space
INDENTATION_WIDTH = 40			# Pixels / indent level

class Viewer(formatter.AbstractWriter):

    """A viewer is mostly a fancy text widget with scroll bars.

    It also doubles as the 'writer' for a Formatter.

    """

    def __init__(self, master, browser=None, context=None, stylesheet=None,
		 width=80, height=40, name="", scrolling="auto",
		 parent=None):
	formatter.AbstractWriter.__init__(self)
	self.master = master
	if not browser:
	    if parent:
		browser = parent.context.browser
	self.context = context or Context(self, browser)
	self.prefs = self.context.app.prefs
	self.stylesheet = stylesheet
	self.current_style = None
	self.name = name
	self.scrolling = scrolling
	self.parent = parent
	self.subwindows = []
	self.rules = []
	self.subviewers = []
	self.resize_interests = [self.__class__.resize_rules]
	self.reset_interests = [self.__class__.clear_targets]
	self.current_cursor = CURSOR_NORMAL
	self.create_widgets(width=width, height=height)
	self.reset_state()
	self.freeze()
	self.text.bind('<Configure>', self.resize_event)
	self._atemp = []
	self.current_index = None
	self.popup_menu = None
	self.status = StringVar()
	self.linkinfo = ""
	if self.context.viewer is self:
	    self.frame.bind('<Enter>', self.enter_frame)
	if self.parent:
	    self.parent.add_subviewer(self)
	self.message("")

	self.prefs.AddGroupCallback('styles-common',
				    self.configure_styles_hard)
	self.prefs.AddGroupCallback('styles',
				    self.configure_styles)

    def message(self, message):
	if not self.context or self.linkinfo:
	    return
	if self.name:
	    message = "%s: %s" % (self.name, message)
	self.status.set(message)
	if not self.parent:
	    self.context.browser.messagevariable(self.status)
	if self.context.busy() and self.context.viewer is self:
	    cursor = CURSOR_WAIT
	else:
	    cursor = CURSOR_NORMAL
	self.set_cursor(cursor)

    def enter_frame(self, event):
	self.context.browser.messagevariable(self.status)

    def reset_state(self):
	self.fonttag = None		# Tag specifying font
	self.margintag = None		# Tag specifying margin
	self.marginlevel = 0		# Numeric margin level
	self.spacingtag = None		# Tag specifying spacing
	self.addtags = ()		# Additional tags (e.g. anchors)
	self.align = None		# Alignment setting
	self.pendingdata = ''		# Data 'on hold'
	self.targets = {}		# Mark names for anchors/footnotes
	self.new_tags()

    def __del__(self):
	self.close()

    def close(self):
	context = self.context
	if context and context.viewer is self:
	    context.stop()
	if context:
	    self.clear_reset()
	    self.context = None
	frame = self.frame
	if frame:
	    self.text = None
	    frame.destroy()
	    self.frame = None
	parent = self.parent
	if parent:
	    parent.remove_subviewer(self)
	    self.parent = None

    def create_widgets(self, width, height):
	bars = self.scrolling == "auto" or self.scrolling
	self.smoothscroll = bars and self.context.app.prefs.GetBoolean(
	    "browser", "smooth-scroll-hack")
	if self.smoothscroll:
	    from supertextbox import make_super_text_box
	    self.text, self.frame = make_super_text_box(self.master,
						      width=width,
						      height=height,
						      hbar=bars, vbar=bars)
	else:
	    self.text, self.frame = tktools.make_text_box(self.master,
						      width=width,
						      height=height,
						      hbar=bars, vbar=bars)
	if self.parent:
	    self.text.config(background=self.parent.text['background'],
			     foreground=self.parent.text['foreground'])
	self.text.config(padx=10, cursor=self.current_cursor)
	self.default_bg = self.text['background']
	self.default_fg = self.text['foreground']
	self.text.config(selectbackground='yellow', insertwidth=0)
	self.configure_styles()
	if self.parent:
	    link = self.parent.text.tag_config('a', 'foreground')[-1]
	    vlink = self.parent.text.tag_config('ahist', 'foreground')[-1]
	    alink = self.parent.text.tag_config('atemp', 'foreground')[-1]
	    self.text.tag_config('a', foreground=link)
	    self.text.tag_config('ahist', foreground=vlink)
	    self.text.tag_config('atemp', foreground=alink)
	self.configure_tags_fixed()
	if self.context.viewer is self:
	    self.text.config(takefocus=1)
	self.text.bind("<Tab>", self.tab_event)
	self.text.bind("<Shift-Tab>", self.shift_tab_event)
	self.text.bind("<Button-1>", self.button_1_event)
	self.text.bind("<Button-2>", self.button_2_event)
	self.text.bind("<Button-3>", self.button_3_event)

    def configure_styles_hard(self):
	"""Force a full reconfigure of styles."""
	self.current_style = None
	self.configure_styles()

    def configure_styles(self):
	"""Used on widget creation, clear, and as a callback when style
	preferences change."""
	selected_style = self.prefs.Get('styles', 'group')
	if not self.stylesheet or (self.current_style != selected_style):
	    self.current_style = selected_style
	    self.stylesheet = DefaultStylesheet(self.prefs,
						self.current_style)
	self.configure_tags(self.stylesheet)

    def configure_tags(self, stylesheet):
	# Self.text would be gone if the viewer was dismissed, in which
	# case we need do no work:
	if self.text:
	    self.text.config(stylesheet.default)
	    for tag, cnf in stylesheet.styles.items():
		self.text.tag_config(tag, cnf)
	    for tag, cnf in stylesheet.history.items():
		self.text.tag_config(tag, cnf)
	    for tag, abovetag in stylesheet.priorities.items():
		self.text.tag_raise(tag, abovetag)

    def configure_tags_fixed(self):
	# These are used in aligning block-level elements:
	self.text.tag_config('right', justify = 'right')
	self.text.tag_config('center', justify = 'center')
	#  Typographic controls:
	self.text.tag_config('underline', underline = 1)
	self.text.tag_config('overstrike', overstrike = 1)
	self.text.tag_config('red', foreground = 'red')
	self.text.tag_config('ins', foreground = 'darkgreen')
	#  Special fonts:
	if DINGBAT_FONT:
	    self.text.tag_config('dingbat', font = DINGBAT_FONT)
	if SYMBOL_FONT:
	    self.text.tag_config('symbol', font = SYMBOL_FONT)
	# Configure margin tags
	for level in range(1, 20):
	    pix = level * INDENTATION_WIDTH
	    self.text.tag_config('margin_%d' % level,
				 lmargin1=pix, lmargin2=pix)
	    tabs = "%d right %d left" % (pix-5, pix)
	    self.text.tag_config('label_%d' % level,
				 lmargin1=pix-INDENTATION_WIDTH, tabs=tabs)
	self.text.tag_config('blockquote', rmargin = INDENTATION_WIDTH)
	# Configure anchor tags
	for tag in 'a', 'ahist':
	    self.text.tag_bind(tag, '<ButtonRelease-1>', self.anchor_click)
	    self.text.tag_bind(tag, '<ButtonRelease-2>', self.anchor_click_new)
	    self.text.tag_bind(tag, '<Leave>', self.anchor_leave)

    def bind_anchors(self, tag):
	# Each URL must have a separate binding so moving between
	# adjacent anchors updates the URL shown in the feedback area
	self.text.tag_bind(tag, '<Enter>', self.anchor_enter)
	# XXX Don't tag bindings need to be garbage-collected?

    def register_interest(self, interests, func):
	interests.append(func)

    def unregister_interest(self, interests, func):
	found = -1
	for i in range(len(interests)):
	    if interests[i] == func:
		found = i
	if found < 0:
	    print "resize interest", func, "not registered"
	    return
	del interests[found]

    def register_reset_interest(self, func):
	self.register_interest(self.reset_interests, func)

    def unregister_reset_interest(self, func):
	self.unregister_interest(self.reset_interests, func)

    def register_resize_interest(self, func):
	self.register_interest(self.resize_interests, func)

    def unregister_resize_interest(self, func):
	self.unregister_interest(self.resize_interests, func)

    def clear_reset(self):
	self._atemp = []
	for func in self.reset_interests[:]:
	    func(self)
	# XXX Eventually the following code should be done using interests too
	subwindows = self.subwindows + self.rules
	subviewers = self.subviewers
	self.subwindows = []
	self.rules = []
	self.subviewers = []
	for viewer in subviewers:
	    viewer.close()
	for w in subwindows:
	    w.destroy()
	if self.text:
	    self.unfreeze()
	    self.text.delete('1.0', END)
	    self.freeze()
	    self.text.config(background=self.default_bg,
			     foreground=self.default_fg)
	    self.configure_styles()
	    self.reset_state()

    def tab_event(self, event):
	w = self.text.tk_focusNext()
	if w:
	    w.focus_set()
	return 'break'

    def shift_tab_event(self, event):
	w = self.text.tk_focusPrev()
	if w:
	    w.focus_set()
	return 'break'

    def button_1_event(self, event):
	self.context.viewer.text.focus_set()
	self.current_index = self.text.index(CURRENT) # For anchor_click

    def button_2_event(self, event):
	self.current_index = self.text.index(CURRENT) # For anchor_click_new

    def button_3_event(self, event):
	if not self.popup_menu:
	    self.create_popup_menu()
	self.popup_menu.tk_popup(event.x_root, event.y_root)

    def create_popup_menu(self):
	self.popup_menu = menu = Menu(self.text, tearoff=0)
	menu.add_command(label="Back in Frame", command=self.context.go_back)
	menu.add_command(label="Reload Frame",
			 command=self.context.reload_page)
	menu.add_command(label="Forward in Frame",
			 command=self.context.go_forward)
	menu.add_separator()
	menu.add_command(label="Frame History...",
			 command=self.context.show_history_dialog)
	menu.add_separator()
	menu.add_command(label="View Frame Source",
			 command=self.context.view_source)
	menu.add_separator()
	menu.add_command(label="Print Frame...",
			 command=self.context.print_document)
	menu.add_command(label="Save Frame As...",
			 command=self.context.save_document)

    def resize_event(self, event):
	for func in self.resize_interests:
	    func(self)

    def resize_rules(self):
	if self.rules:
	    width = self.rule_width()
	    for rule in self.rules:
		if rule._width:
		    rule['width'] = min(rule._width, width)
		else:
		    rule['width'] = int(rule._percent * width)

    def unfreeze(self):
	self.text['state'] = NORMAL

    def freeze(self):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	if self.smoothscroll:
	    from supertextbox import resize_super_text_box
	    resize_super_text_box(frame=self.frame)
	self.text['state'] = DISABLED
	self.text.update_idletasks()

    def flush(self):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''

    def new_tags(self):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	self.flowingtags = filter(
	    None,
	    (self.align, self.fonttag, self.margintag, self.spacingtag) \
	    + self.addtags)

    def scroll_page_down(self, event=None):
	self.text.tk.call('tkScrollByPages', self.text.vbar, 'v', 1)

    def scroll_page_up(self, event=None):
	self.text.tk.call('tkScrollByPages', self.text.vbar, 'v', -1)

    def scroll_line_down(self, event=None):
	self.text.tk.call('tkScrollByUnits', self.text.vbar, 'v', 1)

    def scroll_line_up(self, event=None):
	self.text.tk.call('tkScrollByUnits', self.text.vbar, 'v', -1)

    # AbstractWriter methods

    def new_alignment(self, align):
	if align == 'left': align = None
	self.align = align
	self.new_tags()

    def new_font(self, font):
##	print "New font:", font
	if not font:
	    self.fonttag = None
	else:
	    tag, i, b, tt = font
	    tag = tag or ''
	    if tt: tag = tag + '_tt'
	    if b: tag = tag + '_b'
	    if i: tag = tag + '_i'
	    self.fonttag = tag or None
	self.new_tags()

    def new_margin(self, margin, level):
##	print "New margin:", margin, level
	self.marginlevel = level
	self.margintag = 'margin_%d' % level
	self.new_tags()

    def new_spacing(self, spacing):
	self.spacingtag = spacingtag
	self.new_tags()

    def new_styles(self, styles):
##	print 'New styles:', styles
	self.addtags = styles
	self.new_tags()

    def send_paragraph(self, blankline):
	self.pendingdata = self.pendingdata + ('\n' * blankline)
##	self.text.update_idletasks()

    def send_line_break(self):
	self.pendingdata = self.pendingdata + '\n'
##	self.text.update_idletasks()

    def send_hor_rule(self, abswidth=None, percentwidth=1.0,
		      height=None, align=None):
	width = self.rule_width()
	if abswidth:
	    width = min(width, abswidth)
	elif percentwidth:
	    width = min(width, int(percentwidth * width))
	bgcolor = self.text['background']
	window = Canvas(self.text, borderwidth=1, relief=SUNKEN,
			width=width, height=max((height or 0) - 2, 0),
			background=bgcolor, highlightbackground=bgcolor,
			highlightthickness=0)
	window._width = abswidth	# store for resizing
	window._percent = percentwidth
	self.rules.append(window)
	self.prepare_for_insertion(align)
	self.add_subwindow(window)
	del self.subwindows[-1]
	self.pendingdata = '\n'
##	self.text.update_idletasks()

    def rule_width(self):
	return (self.text.winfo_width()
		- 12 - 2*string.atoi(self.text['padx'])
		- self.marginlevel*INDENTATION_WIDTH
		- ((('blockquote' in self.addtags) and 1 or 0)
		   *INDENTATION_WIDTH))

    def send_label_data(self, data):
##	print "Label data:", `data`
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	tags = self.flowingtags + ('label_%d' % self.marginlevel,)
	if type(data) is StringType:
	    self.text.insert(END, '\t%s\t' % data, tags)
	elif type(data) is InstanceType:
	    #  Some sort of image specified by DINGBAT or SRC
	    self.text.insert(END, '\t', tags)
	    window = Label(self.text, image = data,
			   background = self.text['background'],
			   borderwidth = 0)
	    self.add_subwindow(window)
	    self.pendingdata = '\t'
	elif type(data) is TupleType:
	    #  (string, fonttag) pair
	    if data[1]:
		self.text.insert(END, '\t', tags)
		self.text.insert(END, data[0], tags + (data[1],))
		self.pendingdata = '\t'
	    else:
		self.text.insert(END, '\t%s\t' % data[0], tags)

    def send_flowing_data(self, data):
##	print "Flowing data:", `data`, self.flowingtags
	self.pendingdata = self.pendingdata + data

    def send_literal_data(self, data):
##	print "Literal data:", `data`, self.literaltags
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	self.text.insert(END, data, self.flowingtags + ('pre',))

    # Viewer's own methods

    def anchor_enter(self, event):
	url, target = self.split_target(self.find_tag_url())
	#if url:
	#    if url[0] != '#':
	#	url = self.context.get_baseurl(url)
	#else:
	url = url or "???"
	if not target:
	    target = self.context.get_target()
	if target:
	    message = "%s in %s" % (url, target)
	else:
	    message = url
	self.enter_message(message)

    def enter_message(self, message):
	self.linkinfo = message
	self.status.set(message)
	self.context.browser.messagevariable(self.status)
	self.set_cursor(CURSOR_LINK)

    def anchor_leave(self, event):
	self.leave_message()

    def leave_message(self):
	self.linkinfo = ""
	self.context.message_clear()

    def anchor_click(self, event):
	here = self.text.index("@%d,%d" % (event.x, event.y))
	if self.current_index != here:
	    return
	url = self.find_tag_url()
	if url:
	    self.linkinfo = ""
	    url, target = self.split_target(self.context.get_baseurl(url))
	    self.add_temp_tag()
	    self.context.follow(url, target)

    def anchor_click_new(self, event):
	here = self.text.index("@%d,%d" % (event.x, event.y))
	if self.current_index != here:
	    return
	url = self.find_tag_url()
	if url:
	    url, target = self.split_target(url)
	    self.add_temp_tag()
	    self.master.update_idletasks()
	    from Browser import Browser
	    app = self.context.app
	    b = Browser(app.root, app)
	    b.context.load(self.context.get_baseurl(url))
	    self.remove_temp_tag(histify=1)

    def split_target(self, url):
	i = string.find(url, '>')
	if i < 0: return url, ""
	return url[:i], url[i+1:]

    def add_temp_tag(self):
	list = self.find_tag_ranges()
	if list:
	    self._atemp = list
	    for (start, end) in list:
		self.text.tag_add('atemp', start, end)

    def remove_temp_tag(self, histify=0):
	for (start, end) in self._atemp:
	    self.text.tag_remove('atemp', start, end)
	if histify:
	    for (start, end) in self._atemp:
		self.text.tag_add('ahist', start, end)
	self._atemp = []

    def find_tag_ranges(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '>':
		raw = self.text.tag_ranges(tag)
		list = []
		for i in range(0, len(raw), 2):
		    list.append((raw[i], raw[i+1]))
		return list
	return ()

    def find_tag_url(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '>':
		return tag[1:]

    def find_tag_label(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '#':
		return tag[1:]

    def get_cursor(self):
	return self.current_cursor

    def set_cursor(self, cursor):
	if cursor != self.current_cursor:
	    self.text['cursor'] = self.current_cursor = cursor
	    if cursor == CURSOR_WAIT:
		self.text.update_idletasks()

    def scrollpos(self): return self.text.index('@0,0')
    def scroll_to_position(self, pos): self.text.yview(pos)

    def clear_targets(self):
	targs = self.targets.keys()
	if targs:
	    apply(self.text.mark_unset, tuple(targs))

    def add_target(self, fragment):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	self.text.mark_set(fragment, END + ' - 1 char')
	self.text.mark_gravity(fragment, 'left')
	self.targets[fragment] = 1

    def scroll_to(self, fragment):
	fragment = '#' + fragment
	if self.targets.has_key(fragment):
	    r = self.text.tag_nextrange(fragment, '1.0')
	    if not r:
		#  Maybe an empty target; try the mark database:
		try:
		    first = self.text.index(fragment)
		except TclError:
		    return		# unknown mark
		#  Highlight the entire line:
		r = (first,
		     `1 + string.atoi(string.splitfields(first,'.')[0])` \
		     + '.0')
	else:
	    r = self.parse_range(fragment)
	    if not r:
		return
	first, last = r
	self.text.yview(first)
	self.text.tag_remove(SEL, '1.0', END)
	self.text.tag_add(SEL, first, last)

    def clear_selection(self):
	self.text.tag_remove(SEL, '1.0', END)

    def parse_range(self, fragment):
	try:
	    p = self.range_pattern
	except AttributeError:
	    import regex
	    p = regex.compile('#\([0-9]+\.[0-9]+\)-\([0-9]+\.[0-9]+\)')
	    self.range_pattern = p
	if p.match(fragment) == len(fragment):
	    return p.group(1, 2)
	else:
	    return None

    def prepare_for_insertion(self, align=None):
	if align:
	    if align == 'left':
		align = None
	else:
	    align = self.align
	prev_align, self.align = self.align, align
	self.new_tags()
	self.pendingdata = MIN_IMAGE_LEADER
	self.align = prev_align
	self.new_tags()

    def add_subwindow(self, window, align=CENTER, index=END):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	self.subwindows.append(window)
	self.text.window_create(index, window=window, align=align)

    def add_subviewer(self, subviewer):
	if self.pendingdata:
	    self.text.insert(END, self.pendingdata, self.flowingtags)
	    self.pendingdata = ''
	self.subviewers.append(subviewer)

    def remove_subviewer(self, subviewer):
	if subviewer in self.subviewers:
	    self.subviewers.remove(subviewer)

    def make_subviewer(self, master, name="", scrolling="auto"):
	depth = 0
	v = self
	while v:
	    depth = depth + 1
	    v = v.parent
	if depth > 5:
	    return None			# Ridiculous nesting
	viewer = Viewer(master=master,
			browser=self.context.browser,
			stylesheet=self.stylesheet,
			name=name,
			scrolling=scrolling,
			parent=self)
	viewer.context.set_baseurl(self.context.get_baseurl())
	return viewer

    def find_subviewer(self, name):
	if self.name == name:
	    return self
	for v in self.subviewers:
	    v = v.find_subviewer(name)
	    if v:
		return v

    def find_parentviewer(self):
	return self.parent


def test():
    """Test the Viewer class."""
    import sys
    file = "Viewer.py"
    if sys.argv[1:]: file = sys.argv[1]
    f = open(file)
    data = f.read()
    f.close()
    root = Tk()
    v = Viewer(root, None)
    v.handle_data(data)
    root.mainloop()


if __name__ == '__main__':
    test()
