"""mailto: URI scheme."""

from Tkinter import *
import tktools
import os

from __main__ import app
from assert import assert


META, DATA, DONE = 'META', 'DATA', 'DONE'

class mailto_access:

    def __init__(self, url, method, params):
	toplevel = MailDialog(app.root, url)
	self.state = META

    def pollmeta(self):
	assert(self.state == META)
	return "Ready", 1

    def getmeta(self):
	assert(self.state == META)
	self.state = DATA
	return 204, "No data", {}

    def polldata(self):
	assert(self.state == DATA)
	return "Ready", 1

    def getdata(self, maxbytes):
	assert(self.state == DATA)
	self.state = DONE
	return ""

    def fileno(self):
	return -1

    def close(self):
	pass


SENDMAIL = "/usr/lib/sendmail -t" # XXX

TEMPLATE ="""\
To: %(to)s
Subject: %(subject)s

"""

class MailDialog:

    template = TEMPLATE

    def __init__(self, master, address):
	self.master = master
	self.root = Toplevel(self.master)
	self.root.title("Mail Dialog")
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
	    'to': address,
	    'subject': "",		# XXX
	    }
	self.text.insert(END, self.template % variables)

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
