"""Viewer class for web browser."""


from Tkinter import *
import tktools


class Viewer:

    """A viewer is mostly a fancy text widget with a scroll bar."""

    def __init__(self, master, browser=None, stylesheet=None):
	self.master = master
	self.browser = browser
	self.stylesheet = stylesheet
	self.subwindows = []
	self.create_widgets()

    def create_widgets(self):
	self.text, self.frame = tktools.make_text_box(self.master)
	if self.stylesheet:
	    self.configure_tags(self.stylesheet)
	self.bind_anchors()

    def configure_tags(self, stylesheet):
	self.text.config(stylesheet.default)
	for tag, cnf in stylesheet.para_styles.items():
	    self.text.tag_config(tag, cnf)
	for tag, cnf in stylesheet.char_styles.items():
	    self.text.tag_config(tag, cnf)

    def bind_anchors(self):
	self.text.tag_bind('a', '<Enter>', self.anchor_enter)
	self.text.tag_bind('a', '<Leave>', self.anchor_leave)
	self.text.tag_bind('a', '<ButtonRelease-1>', self.anchor_click)

    def clear_reset(self):
	subwindows = self.subwindows
	self.subwindows = []
	for w in subwindows:
	    w.destroy()
	self.text.delete('0.0', 'end')

    def anchor_enter(self, event):
	url = self.find_tag_url() or '???'
	self.browser.message(url)

    def anchor_leave(self, event):
	self.browser.message()

    def anchor_click(self, event):
	url = self.find_tag_url()
	if url:
	    self.browser.follow(url)

    def find_tag_url(self):
	for tag in self.text.tag_names('current'):
	    if tag[0] == '>':
		return tag[1:]

    def find_tag_label(self):
	for tag in self.text.tag_names('current'):
	    if tag[0] == '#':
		return tag[1:]

    def get_cursor(self):
	return self.text['cursor']

    def set_cursor(self, cursor):
	self.text['cursor'] = cursor

    def add_data(self, data, tags = ()):
	self.text.insert('end', data, tags)

    def scroll_to(self, fragment):
	r = self.text.tag_nextrange('#' + fragment, '1.0')
	if not r:
	    return
	first, last = r
	self.text.yview(first)
	self.text.tag_remove('sel', '1.0', 'end')
	self.text.tag_add('sel', first, last)

    def add_subwindow(self, window):
	self.subwindows.append(window)
	self.text.window_create('end', window=window)


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
    v.add_data(data)
    root.mainloop()


if __name__ == '__main__':
    test()
