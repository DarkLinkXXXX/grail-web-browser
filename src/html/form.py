"""HTML <FORM> tag support (and <INPUT>, etc.).

XXX TO DO:

- METHOD=POST
- <TEXTAREA>

XXX less urgent to do:

- pop-up menus in <SELECT>
- map return to tab if there are multiple text input fields???
- scrollbars in <SELECT> listboxes

"""

import string
from Tkinter import *
import urllib

# ------ Forms

def start_form(parser, attrs):
    action = ''
    method = ''
    enctype = ''
    for a, v in attrs:
	if a == 'action': action = v
	if a == 'method': method = v
	if a == 'enctype': enctype = v
    form_bgn(parser, action, method, enctype)

def end_form(parser):
    form_end(parser)

def do_input(parser, attrs):
    type = ''
    options = {}
    for a, v in attrs:
	if a == 'type': type = string.lower(v)
	else: options[a] = v
    handle_input(parser, type, options)

def start_select(parser, attrs):
    name = ''
    size = 0
    multiple = 0
    for a, v in attrs:
	if a == 'multiple': multiple = 1
	if a == 'name': name = v
	if a == 'size':
	    try: size = string.atoi(v)
	    except: pass
    select_bgn(parser, name, size, multiple)

def end_select(parser):
    select_end(parser)

def do_option(parser, attrs):
    value = ''
    selected = 0
    for a, v in attrs:
	if a == 'value': value = v
	if a == 'selected': selected = 1
    handle_option(parser, value, selected)

def start_textarea(parser, attrs):
    name = ''
    rows = 0
    cols = 0
    for a, v in attrs:
	if a == 'name': name = v
	if a == 'rows':
	    try: rows = string.atoi(v)
	    except: pass
	if a == 'cols':
	    try: cols = string.atoi(v)
	    except: pass
    textarea_bgn(parser, name, rows, cols)

def end_textarea(parser):
    textarea_end(parser)

# --- Hooks for forms

def form_bgn(parser, action, method, enctype):
    if not hasattr(parser, 'form_stack'):
	parser.form_stack = []
	parser.forms = []
    fi = FormInfo(parser, action, method, enctype)
    parser.form_stack.append(fi)

def form_end(parser):
    fi = get_forminfo(parser)
    if fi:
	del parser.form_stack[-1]
	parser.forms.append(fi)
	fi.done()

def handle_input(parser, type, options):
    fi = get_forminfo(parser)
    if fi: fi.do_input(type, options)

def select_bgn(parser, name, size, multiple):
    fi = get_forminfo(parser)
    if fi: fi.start_select(name, size, multiple)

def select_end(parser):
    fi = get_forminfo(parser)
    if fi: fi.end_select()

def handle_option(parser, value, selected):
    fi = get_forminfo(parser)
    if fi: fi.do_option(value, selected)

def textarea_bgn(parser, name, rows, cols):
    fi = get_forminfo(parser)
    if fi: fi.start_textarea(name, rows, cols)

def textarea_end(parser):
    fi = get_forminfo(parser)
    if fi: fi.end_textarea()

# --- Form state tacked on the parser

def get_forminfo(parser):
    if hasattr(parser, 'form_stack'):
	if parser.form_stack:
	    return parser.form_stack[-1]
    return None

class FormInfo:

    def __init__(self, parser, action, method, enctype):
	self.parser = parser
	self.action = action or ''
	self.method = method or 'get'
	self.enctype = enctype
	self.viewer = parser.viewer
	self.inputs = []
	self.radios = {}
	self.select = None
	self.parser.do_p([])

    def __del__(self):
	pass				# XXX

    def done(self):			# Called for </FORM>
	if self.parser:
	    self.parser.do_p([])
	self.parser = None

    def do_input(self, type, options):
	type = string.lower(type) or 'text'
	classname = 'Input' + string.upper(type[0]) + type[1:]
	if hasattr(self, classname):
	    klass = getattr(self, classname)
	    klass(self, options)
	else:
	    print "*** Form with <INPUT TYPE=%s> not supported ***" % type

    def submit_command(self):
	query = ''
	for i in self.inputs:
	    v = i.get()
	    if v:
		if type(v) != type([]):
		    v = [v]
		for vv in v:
		    s = '&' + quote(i.name) + '=' + quote(vv)
		    query = query + s
	if string.lower(self.method) == 'get':
	    url = self.action + '?' + query[1:]
	    self.viewer.browser.follow(url)
	else:
	    print "*** Form with METHOD=%s not supported ***" % self.method

    def reset_command(self):
	for i in self.inputs:
	    i.reset()

    def start_select(self, name, size, multiple):
	self.select = Select(self, name, size, multiple)

    def end_select(self):
	if self.select:
	    self.select.done()
	    self.select = None

    def do_option(self, value, selected):
	if self.select:
	    self.select.do_option(value, selected)

    def start_textarea(self, name, rows, cols):
	self.parser.start_pre([])	# XXX

    def end_textarea(self):
	self.parser.end_pre()		# XXX

    # The following classes are nested with a reason!

    class Input:

	name = ''
	value = ''

	def __init__(self, fi, options):
	    self.fi = fi
	    self.viewer = fi.viewer
	    self.options = options
	    self.getopt('name')
	    self.getopt('value')
	    self.getoptions()
	    self.w = None
	    self.setup()
	    self.reset()
	    self.fi.inputs.append(self)
	    if self.w:
		self.fi.parser.add_subwindow(self.w)

	def getoptions(self):
	    pass

	def setup(self):
	    pass

	def reset(self):
	    pass

	def get(self):
	    return None

	def getopt(self, key):
	    if self.options.has_key(key):
		setattr(self, key, self.options[key])

    class InputText(Input):

	size = 0
	maxlength = None
	show = None

	def getoptions(self):
	    self.getopt('size')

	def setup(self):
	    self.w = Entry(self.viewer.text)
	    self.w.bind('<Return>', self.return_event)
	    if self.size:
		self.w['width'] = self.size
	    if self.show:
		self.w['show'] = self.show

	def reset(self):
	    self.w.delete(0, END)
	    self.w.insert(0, self.value)

	def get(self):
	    return self.w.get()

	def return_event(self, event):
	    self.fi.submit_command()

    class InputPassword(InputText):

	show = '*'

    class InputCheckbox(Input):

	checked = 0

	def getoptions(self):
	    self.getopt('checked')

	def setup(self):
	    self.var = StringVar()
	    self.w = Checkbutton(self.viewer.text, variable=self.var,
				 offvalue='', onvalue=self.value)

	def reset(self):
	    self.var.set(self.checked and self.value or '')

	def get(self):
	    return self.var.get()

    class InputRadio(InputCheckbox):

	def setup(self):
	    if not self.fi.radios.has_key(self.name):
		self.fi.radios[self.name] = StringVar()
		self.first = 1
	    else:
		self.first = 0
	    self.var = self.fi.radios[self.name]
	    self.w = Radiobutton(self.viewer.text, variable=self.var,
				 value=self.value)

	def reset(self):
	    if self.first:
		self.var.set('')
	    if self.checked:
		self.var.set(self.value)

	def get(self):
	    if self.first:
		return self.var.get()

    class InputHidden(Input):

	def get(self):
	    return self.value

    class InputSubmit(Input):

	value = "Submit"

	def setup(self):
	    self.w = Button(self.viewer.text,
			    text=self.value,
			    command=self.fi.submit_command)

    class InputReset(Input):

	value = "Reset"

	def setup(self):
	    self.w = Button(self.viewer.text,
			    text=self.value,
			    command=self.fi.reset_command)


class Select:

    def __init__(self, fi, name, size, multiple):
	self.fi = fi
	self.viewer = fi.viewer
	self.parser = fi.parser
	self.name = name
	self.size = size
	self.multiple = multiple
	self.option = None
	self.options = []
	self.parser.save_bgn()

    def done(self):
	self.end_option()
	size = self.size or 4
	size = min(len(self.options), size)
	size = max(1, size)
	self.w = Listbox(self.viewer.text, height=size, exportselection=0)
	if self.multiple:
	    self.w['selectmode'] = 'extended'
	for v, s, t in self.options:
	    self.w.insert(END, t)
	self.reset()
	self.fi.inputs.append(self)
	self.parser.add_subwindow(self.w)

    def reset(self):
	self.w.select_clear(0, END)
	any = 0
	for i in range(len(self.options)):
	    v, s, t = self.options[i]
	    if s:
		self.w.select_set(i)
		any = 1
	if not any and self.options:
	    self.w.select_set(0)

    def get(self):
	list = []
	for i in range(len(self.options)):
	    v, s, t = self.options[i]
	    if self.w.select_includes(i):
		list.append(v or t)
	return list

    def do_option(self, value, selected):
	self.end_option()
	self.parser.save_bgn()
	self.option = (value, selected)

    def end_option(self):
	text = self.parser.save_end()
	if self.option:
	    value, selected = self.option
	    self.option = None
	    self.options.append((value, selected, text))


def quote(s):
    w = string.splitfields(s, ' ')
    w = map(urllib.quote, w)
    return string.joinfields(w, '+')
