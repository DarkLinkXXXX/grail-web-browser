from Tkinter import Entry
import string
import urllib

ATTRIBUTES_AS_KEYWORDS = 1

def do_isindex(parser, attrs):
    try:
	prompt = attrs['prompt']
    except KeyError:
	prompt = "This is a searchable index. Enter search keywords:"

    IndexWidget(parser, prompt,
		(attrs.has_key('href') and attrs['href']) or None)


class IndexWidget:

    def __init__(self, parser, prompt, url):
	self.query_url = url
	viewer = parser.viewer
	self.context = viewer.context
	self.w = Entry(viewer.text)
	self.w.bind('<Return>', self.submit)
	viewer.send_hor_rule()
	viewer.send_flowing_data(prompt)
	parser.add_subwindow(self.w)
	viewer.send_line_break()
	viewer.send_hor_rule()

    def submit(self, event):
	data = self.w.get()
	url = self.query_url or self.context.baseurl()
	i = string.find(url, '?')
	if i >= 0:
	    url = url[:i]
	url = url + '?' + quote(data)
	self.context.load(url)

def quote(s):
    w = string.splitfields(s, ' ')
    w = map(urllib.quote, w)
    return string.joinfields(w, '+')
