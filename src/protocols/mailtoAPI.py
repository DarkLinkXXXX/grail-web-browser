"""mailto: URI scheme handler."""

from Tkinter import *
import tktools
import os
import sys
import time

from __main__ import app, GRAILVERSION
from nullAPI import null_access
from Context import LAST_CONTEXT

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
	self.master = master
	self.root = tktools.make_toplevel(self.master,
					  title="Mail Dialog")
	self.text, self.frame = tktools.make_text_box(self.root, 80, 24)
	self.botframe = Frame(self.root)
	self.botframe.pack(fill=X)
	self.send_button = Button(self.botframe,
				  text="Send",
				  command=self.send_command)
	self.send_button.pack(side=LEFT)
	self.cancel_button = Button(self.botframe,
				    text="Cancel",
				    command=self.cancel_command)
	self.cancel_button.pack(side=RIGHT)
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
	self.text.insert(END, self.template % variables + (data or ''))

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

    def cancel_command(self):
	self.root.destroy()
