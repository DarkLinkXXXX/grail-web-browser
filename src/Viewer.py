"""Viewer class for web browser."""


from Tkinter import *
import tktools
import formatter
import string


class Viewer(formatter.AbstractWriter):

    """A viewer is mostly a fancy text widget with a scroll bar.

    It also doubles as the 'writer' for a Formatter.

    """

    def __init__(self, master, browser=None, stylesheet=None, height=40):
	formatter.AbstractWriter.__init__(self)
	self.master = master
	self.browser = browser
	self.stylesheet = stylesheet
	self.subwindows = []
	self.rules = []
	self.create_widgets(height)
	self.fonttag = None		# Tag specifying font
	self.margintag = None		# Tag specifying margin
	self.marginlevel = 0		# Numeric margin level
	self.spacingtag = None		# Tag specifying spacing
	self.addtags = ()		# Additional tags (e.g. anchors)
	self.tags = ()			# Near-final collection of tags
	self.literaltags = ()		# Tags for literal text
	self.flowingtags = ()		# Tags for flowed text
	self.freeze()
	self.text.bind('<Configure>', self.resize_event)

    def create_widgets(self, height):
	self.text, self.frame = tktools.make_text_box(self.master,
						      height=height,
						      hbar=1, vbar=1)
	self.text['insertwidth'] = 0
	if self.stylesheet:
	    self.configure_tags(self.stylesheet)

    def configure_tags(self, stylesheet):
	self.text.config(stylesheet.default)
	for tag, cnf in stylesheet.styles.items():
	    self.text.tag_config(tag, cnf)
	# Configure margin tags
	for level in range(1, 20):
	    pix = level*40
	    self.text.tag_config('margin_%d' % level,
				 lmargin1=pix, lmargin2=pix)
	    tabs = "%d right %d left" % (pix-5, pix)
	    self.text.tag_config('label_%d' % level,
				 lmargin1=pix-40, tabs=tabs)

    def bind_anchors(self, tag):
	self.text.tag_bind(tag, '<Enter>', self.anchor_enter)
	self.text.tag_bind(tag, '<Leave>', self.anchor_leave)
	self.text.tag_bind(tag, '<ButtonRelease-1>', self.anchor_click)
	# XXX Don't tag bindings need to be garbage-collected?

    def clear_reset(self):
	subwindows = self.subwindows + self.rules
	self.subwindows = []
	self.rules = []
	for w in subwindows:
	    w.destroy()
	self.unfreeze()
	self.text.delete('1.0', END)
	self.freeze()

    def resize_event(self, event):
	# Needl to reconfigure all the horizontal rools :-(
	if self.rules:
	    width = self.rule_width()
	    for rule in self.rules:
		rule['width'] = width

    def unfreeze(self):
	self.text['state'] = NORMAL

    def freeze(self):
	self.text['state'] = DISABLED

    def new_tags(self):
	self.tags = filter(None,
			   (self.fonttag, self.margintag, self.spacingtag) +
			   self.addtags)
	self.literaltags = self.tags + ('pre',)
	self.flowingtags = self.tags
##	print "New tags:", self.tags

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
	self.addtags = styles
	self.new_tags()

    def send_paragraph(self, blankline):
	self.text.insert(END, '\n' + '\n'*blankline)

    def send_line_break(self):
	self.text.insert(END, '\n')

    def send_hor_rule(self):
	self.text.insert(END, '\n')
	width = self.rule_width()
	window = Canvas(self.text, borderwidth=1, relief=SUNKEN,
			width=width, height=0)
	self.rules.append(window)
	self.text.window_create(END, window=window)
	self.text.insert(END, '\n')

    def rule_width(self):
	width = self.text.winfo_width() - 16
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
	self.browser.enter(url)

    def anchor_leave(self, event):
	self.browser.leave()

    def anchor_click(self, event):
	url = self.find_tag_url()
	if url:
	    self.browser.follow(url)

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
