# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI.License/Grail-Version-0.3",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

"""mailto: URI scheme handler."""

from Tkinter import *
import tktools
import os
import sys
import time
import string
import cgi
from urlparse import urlparse, urlunparse

from __main__ import app, GRAILVERSION
from nullAPI import null_access
from Context import LAST_CONTEXT


# Python 1.4 has a new, very useful function!
if hasattr(string, 'capwords'):
    capwords = string.capwords
else:
    # the python implementation of Python 1.4's string.capwords()
    def capwords(str, sep=None):
	cappedwords = []
	if sep is None:
	    words = string.split(str)
	else:
	    words = string.splitfields(str, sep)
	for word in words:
	    cappedwords.append(string.upper(word[0]) + string.lower(word[1:]))
	if sep is None:
	    return string.join(cappedwords)
	else:
	    return string.joinfields(cappedwords, sep)


class mailto_access(null_access):

    def __init__(self, url, method, params, data=None):
	null_access.__init__(self, url, method, params)
	# when a form's action is a mail URL, the data field will be
	# non-None.  In that case, initialize the dialog with the data
	# contents
	toplevel = MailDialog(app.root, url, data)

if os.sys.platform[:3] == 'sco': 
    # Use MMDF instead of sendmail
    SENDMAIL = "/usr/mmdf/bin/submit -mtlrxto,cc\'*\'s"
    # submit needs a Date: field or it will not include it
    TEMPLATE ="""\
To: %(to)s
Date: %(date)s
Subject: %(subject)s
MIME-Version: 1.0
Content-Type: %(ctype)s
X-Mailer: %(mailer)s
X-URL: %(url)s
"""
else:
    SENDMAIL = "/usr/lib/sendmail -t" # XXX
    TEMPLATE ="""\
To: %(to)s
Subject: %(subject)s
MIME-Version: 1.0
Content-Type: %(ctype)s
X-Mailer: %(mailer)s
X-URL: %(url)s
"""


class MailDialog:

    template = TEMPLATE

    def __init__(self, master, address, data):
	# query semantics may be used to identify header field values
	scheme, netloc, path, params, query, fragment = urlparse(address)
	address = urlunparse((scheme, netloc, path, '', '', ''))
	headers = cgi.parse_qs(query)
	# create widgets
	self.master = master
	self.root = tktools.make_toplevel(self.master,
					  title="Mail Dialog")
	self.root.protocol("WM_DELETE_WINDOW", self.cancel_command)
	self.root.bind("<Alt-w>", self.cancel_command)
	self.root.bind("<Alt-W>", self.cancel_command)
	fr, top, botframe = tktools.make_double_frame(self.root)
	self.text, fr = tktools.make_text_box(top, 80, 24)
	self.send_button = Button(botframe,
				  text="Send",
				  command=self.send_command)
	self.send_button.pack(side=LEFT)
	self.cancel_button = Button(botframe,
				    text="Cancel",
				    command=self.cancel_command)
	self.cancel_button.pack(side=RIGHT)
	tktools.unify_button_widths(self.send_button, self.cancel_button)
	variables = {
	    'to':	address,
	    'date':	time.ctime(time.time()),
	    'subject':	data and 'Form posted from Grail' or '',
	    'mailer':	GRAILVERSION,
	    'ctype':    data and 'application/x-www-form-urlencoded' \
	                      or """text/plain; charset=us-ascii
Content-Transfer-Encoding: 7bit""",
	    'url':	LAST_CONTEXT and LAST_CONTEXT.get_baseurl() or ''
	    }
	# move default set of query'd headers into variables
	for header, vlist in headers.items():
	    if variables.has_key(header):
		variables[header] = vlist[0] # throw away duplicates
		del headers[header]
	self.text.insert(END, self.template % variables + (data or ''))
	# insert extra headers
	for header, vlist in headers.items():
	    value = vlist[0]		# throw away duplicates
	    self.text.insert(END, '%s: %s\n' % (capwords(header, '-'), value))
	# insert newline
	self.text.insert(END, '\n')

    def send_command(self):
	message = self.text.get("1.0", END)
	if message:
	    self.root['cursor'] = 'watch'
	    self.text['cursor'] = 'watch'
	    self.root.update_idletasks()
	    if message[-1] != '\n': message = message + '\n'
	    p = os.popen(SENDMAIL, 'w')
	    p.write(message)
	    sts = p.close()
	    if sts:
		print "*** Sendmail exit status", sts, "***"
	self.root.destroy()

    def cancel_command(self, event=None):
	self.root.destroy()
