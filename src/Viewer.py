"""Viewer class."""


from Tkinter import *
import tktools
import formatter
import string
from Context import Context
from Cursors import *


class Viewer(formatter.AbstractWriter):

    """A viewer is mostly a fancy text widget with scroll bars.

    It also doubles as the 'writer' for a Formatter.

    """

    def __init__(self, master, browser=None, context=None, stylesheet=None,
		 width=80, height=40, name="", scrolling="auto",
		 parentviewer=None):
	formatter.AbstractWriter.__init__(self)
	self.master = master
	self.context = context or Context(self, browser)
	self.stylesheet = stylesheet
	self.name = name
	self.scrolling = scrolling
	self.parentviewer = parentviewer
	self.subwindows = []
	self.rules = []
	self.subviewers = []
	self.resize_interests = [self.__class__.resize_rules]
	self.reset_interests = []
	self.create_widgets(width=width, height=height)
	self.reset_state()
	self.freeze()
	self.text.bind('<Configure>', self.resize_event)
	self._atemp = []

    def reset_state(self):
	self.fonttag = None		# Tag specifying font
	self.margintag = None		# Tag specifying margin
	self.marginlevel = 0		# Numeric margin level
	self.spacingtag = None		# Tag specifying spacing
	self.addtags = ()		# Additional tags (e.g. anchors)
	self.literaltags = ()		# Tags for literal text
	self.flowingtags = ()		# Tags for flowed text

    def __del__(self):
	self.close()

    def close(self):
	self.context.stop()
	self.clear_reset()
	frame = self.frame
	if frame:
	    self.frame = None
	    self.text = None
	    frame.destroy()
	self.parentviewer = None
	self.context = None		# XXX close it?

    def create_widgets(self, width, height):
	bars = self.scrolling == "auto" or self.scrolling
	self.text, self.frame = tktools.make_text_box(self.master,
						      width=width,
						      height=height,
						      hbar=bars, vbar=bars)
	self.text.config(padx=10, cursor=CURSOR_NORMAL)
	self.default_bg = self.text['background']
	self.default_fg = self.text['foreground']
	self.text.config(selectbackground='yellow')
	if self.stylesheet:
	    self.configure_tags(self.stylesheet)

    def configure_tags(self, stylesheet):
	self.text.config(stylesheet.default)
	for tag, cnf in stylesheet.styles.items():
	    self.text.tag_config(tag, cnf)
	for tag, cnf in stylesheet.history.items():
	    self.text.tag_config(tag, cnf)
	for tag, abovetag in stylesheet.priorities.items():
	    self.text.tag_raise(tag, abovetag)
	# Configure margin tags
	for level in range(1, 20):
	    pix = level*40
	    self.text.tag_config('margin_%d' % level,
				 lmargin1=pix, lmargin2=pix)
	    tabs = "%d right %d left" % (pix-5, pix)
	    self.text.tag_config('label_%d' % level,
				 lmargin1=pix-40, tabs=tabs)
	# Configure anchor tags
	for tag in 'a', 'ahist':
	    self.text.tag_bind(tag, '<ButtonRelease-1>', self.anchor_click)
	    self.text.tag_bind(tag, '<ButtonRelease-2>', self.anchor_click_new)
	    self.text.tag_bind(tag, '<ButtonRelease-3>', self.anchor_click_new)
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
	    self.text.config(background=self.default_bg,
			     foreground=self.default_fg)
	    self.text.delete('1.0', END)
	    self.reset_state()
	    self.freeze()

    def resize_event(self, event):
	for func in self.resize_interests:
	    func(self)

    def resize_rules(self):
	if self.rules:
	    width = self.rule_width()
	    for rule in self.rules:
		rule['width'] = width

    def unfreeze(self):
	self.text['state'] = NORMAL

    def freeze(self):
	self.text['state'] = DISABLED
	self.text.update_idletasks()

    def new_tags(self):
	self.flowingtags = filter(
	    None,
	    (self.fonttag, self.margintag, self.spacingtag)) + self.addtags
	self.literaltags = self.flowingtags + ('pre',)

    def scroll_page_down(self, event=None):
	self.text.tk.call('tkScrollByPages', self.text.vbar, 'v', 1)

    def scroll_page_up(self, event=None):
	self.text.tk.call('tkScrollByPages', self.text.vbar, 'v', -1)

    def scroll_line_down(self, event=None):
	self.text.tk.call('tkScrollByUnits', self.text.vbar, 'v', 1)

    def scroll_line_up(self, event=None):
	self.text.tk.call('tkScrollByUnits', self.text.vbar, 'v', -1)

    # AbstractWriter methods
	
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
	self.addtags = filter(None, styles)
	self.new_tags()

    def send_paragraph(self, blankline):
	self.text.insert(END, '\n' + '\n'*blankline)
##	self.text.update_idletasks()

    def send_line_break(self):
	self.text.insert(END, '\n')
##	self.text.update_idletasks()

    def send_hor_rule(self):
	self.text.insert(END, '\n')
	width = self.rule_width()
	window = Canvas(self.text, borderwidth=1, relief=SUNKEN,
			width=width, height=0,
			background=self.text['background'],
			highlightbackground=self.text['background'])
	self.rules.append(window)
	self.text.window_create(END, window=window)
	self.text.insert(END, '\n')
##	self.text.update_idletasks()

    def rule_width(self):
	width = self.text.winfo_width() - 16 - 2*string.atoi(self.text['padx'])
	return width

    def send_label_data(self, data):
##	print "Label data:", `data`
	tags = self.flowingtags + ('label_%d' % self.marginlevel,)
	self.text.insert(END, '\t'+data+'\t', tags)

    def send_flowing_data(self, data):
##	print "Flowing data:", `data`, self.flowingtags
	self.text.insert(END, data, self.flowingtags)

    def send_literal_data(self, data):
##	print "Literal data:", `data`, self.literaltags
	self.text.insert(END, data, self.literaltags)

    # Viewer's own methods

    def anchor_enter(self, event):
	url = self.find_tag_url() or '???'
	url, target = self.split_target(url)
	if not target:
	    target = self.context.get_target()
	if target:
	    url =  "%s in %s" % (url, target)
	if not self.context.busy():
	    self.text.config(cursor=CURSOR_LINK)
	    self.context.enter(url)

    def anchor_leave(self, event):
	if not self.context.busy():
	    self.text.config(cursor=CURSOR_NORMAL)
	    self.context.leave()

    def anchor_click(self, event):
	url = self.find_tag_url()
	if url:
	    url, target = self.split_target(url)
	    self.add_temp_tag()
	    self.context.follow(url, target)

    def anchor_click_new(self, event):
	url = self.find_tag_url()
	if url:
	    url, target = self.split_target(url)
	    self.add_temp_tag()
	    self.master.update_idletasks()
	    from Browser import Browser
	    from __main__ import app
	    import urlparse
	    b = Browser(self.master, app)
	    b.context.load(self.context.get_baseurl(url))
	    self.remove_temp_tag(histify=1)

    def split_target(self, url):
	i = string.find(url, '>')
	if i < 0: return url, ""
	return url[:i], url[i+1:]

    def add_temp_tag(self):
	start, end = self.find_tag_range()
	if start and end:
	    self._atemp = [start, end]
	    self.text.tag_add('atemp', start, end)

    def remove_temp_tag(self, histify=0):
	if self._atemp:
	    self.text.tag_remove('atemp', self._atemp[0], self._atemp[1])
	    if histify:
		self.text.tag_add('ahist', self._atemp[0], self._atemp[1])
	    self._atemp = []

    def find_tag_range(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '>':
		range = self.text.tag_ranges(tag)
		return range[0], range[1]
	return None, None

    def find_tag_url(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '>':
		return tag[1:]

    def find_tag_label(self):
	for tag in self.text.tag_names(CURRENT):
	    if tag[0] == '#':
		return tag[1:]

    def get_cursor(self):
	return self.text['cursor']

    def set_cursor(self, cursor):
	self.text['cursor'] = cursor

    def scrollpos(self): return self.text.index('@0,0')
    def scroll_to_position(self, pos): self.text.yview(pos)

    def scroll_to(self, fragment):
	r = self.text.tag_nextrange('#' + fragment, '1.0')
	if not r:
	    r = self.parse_range(fragment)
	    if not r:
		return
	first, last = r
	self.text.yview(first)
	self.text.tag_remove(SEL, '1.0', END)
	self.text.tag_add(SEL, first, last)

    def parse_range(self, fragment):
	try:
	    p = self.range_pattern
	except AttributeError:
	    import regex
	    p = regex.compile('\([0-9]+\.[0-9]+\)-\([0-9]+\.[0-9]+\)')
	    self.range_pattern = p
	if p.match(fragment) == len(fragment):
	    return p.group(1, 2)
	else:
	    return None

    def add_subwindow(self, window):
	self.subwindows.append(window)
	self.text.window_create(END, window=window)

    def make_subviewer(self, master, name="", scrolling="auto"):
	self.subwindows.append(master)
	depth = 0
	v = self
	while v:
	    depth = depth + 1
	    v = v.parentviewer
	if depth > 5:
	    return None			# Ridiculous nesting
	viewer = Viewer(master=master,
			browser=self.context.browser,
			stylesheet=self.stylesheet,
			name=name,
			scrolling=scrolling,
			parentviewer=self)
	viewer.context.set_baseurl(self.context.get_baseurl())
	self.subviewers.append(viewer)
	return viewer

    def find_subviewer(self, name):
	if self.name == name:
	    return self
	for v in self.subviewers:
	    v = v.find_subviewer(name)
	    if v:
		return v

    def find_parentviewer(self):
	return self.parentviewer


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
