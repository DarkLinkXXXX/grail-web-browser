from Tkinter import *
import string
import urllib

def do_isindex(parser, attrs):
    IndexWidget(parser)

class IndexWidget:

    def __init__(self, parser):
	self.parser = parser
	self.viewer = self.parser.viewer
	self.context = self.viewer.context
	self.w = Entry(self.viewer.text)
	self.w.bind('<Return>', self.submit)
	self.viewer.send_hor_rule()
	self.viewer.send_flowing_data(
	    "This is a searchable index. Enter search keywords:")
	self.parser.add_subwindow(self.w)
	self.viewer.send_hor_rule()

    def submit(self, event):
	data = self.w.get()
	url = self.context.baseurl()
	i = string.find(url, '?')
	if i >= 0:
	    url = url[:i]
	url = url + '?' + quote(data)
	self.context.load(url)

def quote(s):
    w = string.splitfields(s, ' ')
    w = map(urllib.quote, w)
    return string.joinfields(w, '+')
