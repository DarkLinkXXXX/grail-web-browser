"""HTML <FORM> tag support (and <INPUT>, etc.).

"""

import string
from Tkinter import *
import urllib
import tktools

# ------ Forms

URLENCODED = "application/x-www-form-urlencoded"
FORM_DATA = "multipart/form-data"

def start_form(parser, attrs):
    action = ''
    method = ''
    enctype = URLENCODED
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
	parser.browser.forms = []
    fi = FormInfo(parser, action, method, enctype)
    parser.form_stack.append(fi)

def form_end(parser):
    fi = get_forminfo(parser)
    if fi:
	del parser.form_stack[-1]
	parser.forms.append(fi)
	parser.browser.forms.append(fi)
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
	self.browser = parser.viewer.browser
	self.inputs = []
	self.radios = {}
	self.select = None
	self.parser.do_p([])
	# gather cached form data if we've been to this page before
	formdata_list = self.browser._page.formdata()
	if formdata_list:
	    self.formdata = formdata_list[len(parser.forms)]
	else:
	    self.formdata = []

    def __del__(self):
	pass				# XXX

    def get(self):
	state = []
	for i in self.inputs:
	    value = i.getstate()
	    state.append(value)
	return state

    def done(self):			# Called for </FORM>
	if self.parser:
	    self.parser.do_p([])
	self.parser = None

    def do_input(self, type, options):
	type = string.lower(type) or 'text'
	classname = 'Input' + string.upper(type[0]) + type[1:]
	if hasattr(self, classname):
	    klass = getattr(self, classname)
	    instance = klass(self, options)
	    # update any cached form status
	    if self.formdata:
		instance.set(self.formdata[0])
		del self.formdata[0]
	else:
	    print "*** Form with <INPUT TYPE=%s> not supported ***" % type

    def submit_command(self):
	enctype = string.lower(self.enctype)
	method = string.lower(self.method)
	data = ''
	if enctype == URLENCODED:
	    data = self.make_urlencoded_data()
	elif enctype == FORM_DATA and method == 'post':
	    ctype, data = self.make_form_data()
	if method == 'get' and enctype == URLENCODED:
	    url = self.action + '?' + data
	    self.viewer.browser.follow(url)
	elif method == 'post' and enctype in (URLENCODED, FORM_DATA):
	    if enctype == FORM_DATA:
		enctype = ctype
	    params = {"Content-type": enctype}
	    if enctype == URLENCODED:
		params["Content-length"] = `len(data)`
	    self.viewer.browser.post(self.action, data, params)
	else:
	    print "*** Form with METHOD=%s and ENCTYPE=%s not supported ***" % (
		  self.method, self.enctype)

    def make_urlencoded_data(self):
	data = ''
	for i in self.inputs:
	    if not i.name: continue
	    v = i.get()
	    if v:
		if type(v) != type([]):
		    v = [v]
		for vv in v:
		    s = '&' + quote(i.name) + '=' + quote(vv)
		    data = data + s
	return data[1:]

    def make_form_data(self):
	import ArrayIO
	import MimeWriter
	fp = ArrayIO.ArrayIO()
	mw = MimeWriter.MimeWriter(fp)
	mw.startmultipartbody("form-data")
	for i in self.inputs:
	    if not i.name: continue
	    disp = 'form-data; name="%s"' % i.name
	    v = i.get()
	    data = None
	    if i.__class__.__name__ == 'InputFile':
		try:
		    f = open(v)
		    data = f.read()
		    f.close()
		except IOError, msg:
		    print "IOError:", msg
		else:
		    disp = disp + '; filename="%s"' % v
	    sw = mw.nextpart()
	    sw.addheader("Content-Disposition", disp)
	    if data is not None:
		sw.addheader("Content-Length", str(len(data)))
		body = sw.startbody("text/plain")
		body.write(data)
	    else:
		body = sw.startbody("text/plain")
		body.write(v)
	mw.lastpart()
	fp.seek(0)
	import rfc822
	headers = rfc822.Message(fp)
	ctype = headers['content-type']
	ctype = string.join(string.split(ctype)) # Get rid of newlines
	data = fp.read()
	return ctype, data

    def reset_command(self):
	for i in self.inputs:
	    i.reset()

    def start_select(self, name, size, multiple):
	self.select = Select(self, name, size, multiple)

    def end_select(self):
	if self.select:
	    self.select.done()
	    # update any cached form status
	    if self.formdata:
		self.select.set(self.formdata[0])
		del self.formdata[0]
	    self.select = None

    def do_option(self, value, selected):
	if self.select:
	    self.select.do_option(value, selected)

    def start_textarea(self, name, rows, cols):
	self.textarea = Textarea(self, name, rows, cols)

    def end_textarea(self):
	if self.textarea:
	    self.textarea.done()
	    # update any cached form status
	    if self.formdata:
		self.textarea.set(self.formdata[0])
		del self.formdata[0]
	    self.textarea = None

    # The following classes are nested so we can use getattr(self, 'Input...')

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

	def set(self, value):
	    pass

	def getopt(self, key):
	    if self.options.has_key(key):
		setattr(self, key, self.options[key])

	def getstate(self):
	    # Get raw state for form caching -- default same as get()
	    return self.get()

    class InputText(Input):

	size = 0
	maxlength = None
	show = None

	def getoptions(self):
	    self.getopt('size')

	def setup(self):
	    self.w = self.entry = Entry(self.viewer.text)
	    self.setup_entry()

	def setup_entry(self):
	    self.entry.bind('<Return>', self.return_event)
	    if self.size:
		size = self.size
		i = string.find(size, ',')
		if i >= 0: size = size[:i]
		try:
		    width = string.atoi(size)
		except string.atoi_error:
		    pass
		else:
		    self.entry['width'] = width
	    if self.show:
		self.entry['show'] = self.show

	def reset(self):
	    self.entry.delete(0, END)
	    self.entry.insert(0, self.value)

	def get(self):
	    return self.entry.get()

	def set(self, value):
	    text = ''
	    if type(value) == type(''):
		text = value
	    elif type(value) == type([]) and len(value) > 0:
		text = value[0]
		del value[0]
	    self.entry.delete(0, END)
	    self.entry.insert(0, text)

	def return_event(self, event):
	    self.fi.submit_command()

    class InputPassword(InputText):

	show = '*'

    class InputCheckbox(Input):

	checked = 0
	value = 'on'

	def getoptions(self):
	    self.getopt('checked')

	def setup(self):
	    self.var = StringVar()
	    self.w = Checkbutton(self.viewer.text, variable=self.var,
				 offvalue='', onvalue=self.value)

	def reset(self):
	    self.var.set(self.checked and self.value or '')

	def set(self, value):
	    if self.value == value:
		self.var.set(self.value)

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
	    if self.first:
		self.var.set(self.value)
	    self.w = Radiobutton(self.viewer.text, variable=self.var,
				 value=self.value)

	def reset(self):
	    if self.checked:
		self.var.set(self.value)

	def get(self):
	    if self.first:
		return self.var.get()
	    else:
		return None

	def getstate(self):
	    # Get raw state for form caching
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

	def get(self):
	    if self.w['state'] == ACTIVE:
		return self.value
	    else:
		return None

    class InputReset(Input):

	value = "Reset"

	def setup(self):
	    self.w = Button(self.viewer.text,
			    text=self.value,
			    command=self.fi.reset_command)

    class InputFile(InputText):

	def setup(self):
	    self.w = Frame(self.viewer.text)
	    self.entry = Entry(self.w)
	    self.entry.pack(side=LEFT)
	    self.setup_entry()
	    self.browse = Button(self.w, text="Browse...",
				 command=self.browse_command)
	    self.browse.pack(side=RIGHT)

	def browse_command(self):
	    import FileDialog
	    fd = FileDialog.LoadFileDialog(self.browse)
	    filename = fd.go(self.entry.get())
	    if filename:
		self.set(filename)


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
	if not len(self.options):
	    self.w = None
	    return
	any = 0
	for v, s, t in self.options:
	    if s: any = 1
	if not any:
	    v, s, t = self.options[0]
	    self.options[0] = v, 1, t
	size = self.size
	if size <= 0:
	    if self.multiple: size = 4
	    else: size = 1
	size = min(len(self.options), size)
	if size == 1 and not self.multiple:
	    self.make_menu()
	else:
	    self.make_list(size)

    def make_menu(self):
	self.v = StringVar()
	self.v.set(self.name)
	values = tuple(map(lambda (v,s,t): t, self.options))
	self.w = apply(OptionMenu,
		       (self.viewer.text, self.v) + values)
	self.reset_menu()
	self.fi.inputs.append(self)
	self.parser.add_subwindow(self.w)

    def make_list(self, size):
	self.v = None
	needvbar = len(self.options) > size
	self.w, self.frame = tktools.make_list_box(self.viewer.text,
						   height=size,
						   vbar=needvbar)
	self.w['exportselection'] = 0
	if self.multiple:
	    self.w['selectmode'] = 'extended'
	for v, s, t in self.options:
	    self.w.insert(END, t)
	self.reset_list()
	self.fi.inputs.append(self)
	self.parser.add_subwindow(self.frame)

    def reset(self):
	if not self.w: return
	if self.v:
	    self.reset_menu()
	else:
	    self.reset_list()

    def reset_menu(self):
	for v, s, t in self.options:
	    if s:
		self.v.set(t)
		break

    def reset_list(self):
	self.w.select_clear(0, END)
	for i in range(len(self.options)):
	    v, s, t = self.options[i]
	    if s:
		self.w.select_set(i)

    def get(self):
	# debugging
	if not self.w: return None
	if self.v: return self.get_menu()
	else: return self.get_list()

    def getstate(self):
	return self.get()

    def get_menu(self):
	text = self.v.get()
	for v, s, t in self.options:
	    if text == t: return v or t
	return None

    def get_list(self):
	list = []
	for i in range(len(self.options)):
	    v, s, t = self.options[i]
	    if self.w.select_includes(i):
		list.append(v or t)
	return list

    def set(self, value):
	# debugging
	if not self.w: return
	if self.v: self.set_menu(value)
	else: self.set_list(value)

    def set_menu(self, value):
	for v, s, t in self.options:
	    if value == (v or t):
		self.v.set(t)
		break

    def set_list(self, value):
	self.w.select_clear(0, END)
	for i in range(len(self.options)):
	    v, s, t = self.options[i]
	    if (v or t) in value:
		self.w.select_set(i)

    def do_option(self, value, selected):
	self.end_option()
	self.parser.save_bgn()
	self.option = (value, selected)

    def end_option(self):
	data = string.strip(self.parser.save_end())
	if self.option:
	    value, selected = self.option
	    self.option = None
	    self.options.append((value, selected, data))


class Textarea:

    def __init__(self, fi, name, rows, cols):
	self.fi = fi
	self.parser = fi.parser
	self.viewer = fi.viewer
	self.name = name
	self.rows = rows
	self.cols = cols
	self.parser.nofill = self.parser.nofill+1
	self.parser.save_bgn()

    def done(self):
	data = self.parser.save_end()
	self.parser.nofill = max(0, self.parser.nofill-1)
	if data[:1] == '\n': data = data[1:]
	if data[-1:] == '\n': data = data[:-1]
	self.w, self.frame = tktools.make_text_box(self.viewer.text,
						   width=self.cols,
						   height=self.rows,
						   hbar=1, vbar=1)
	self.w['wrap'] = NONE
	self.data = data
	self.reset()
	self.fi.inputs.append(self)
	self.parser.add_subwindow(self.frame)

    def reset(self):
	self.w.delete("1.0", END)
	self.w.insert(END, self.data)

    def get(self):
	return self.w.get("1.0", END)

    def getstate(self):
	return self.get()

    def set(self, value):
	# TBD: Tk text widget `feature' can cause an extra newline to
	# be inserted each time the text is set.
	if value[-1] == '\n': value = value[:-1]
	self.w.delete("1.0", END)
	self.w.insert(END, value)

def quote(s):
    w = string.splitfields(s, ' ')
    w = map(urllib.quote, w)
    return string.joinfields(w, '+')
