from SafeTkinter import *
from SafeTkinter import _cnfmerge

class Dialog(Frame):

    def __init__(self, master=None,
		 title='', text='', bitmap='', default='', strings=[]):
	self.root = Toplevel(master)
	self.message = Message(self.root, text=text)
	self.message.pack(fill='both', expand=1)
	self.frame = Frame(self.root)
	self.frame.pack(fill='x', expand=1)
	num = 0
	for s in strings:
	    b = Button(self.frame, text=s,
		       command=(lambda self=self, num=num: self.done(num)))
	    b.pack(side='left', fill='both', expand=1)
	    num = num+1
	try:
	    self.root.mainloop()
	except SystemExit:
	    pass
	self.root.destroy()

    def done(self, num):
	self.num = num
	raise SystemExit

def _test():
	d = Dialog(root,  title='File Modified',
			  text=
			  'File "Python.h" has been modified'
			  ' since the last time it was saved.'
			  ' Do you want to save it before'
			  ' exiting the application?',
			  bitmap='questhead',
			  default=0,
			  strings=('Save File', 
				      'Discard Changes', 
				      'Return to Editor'))
	print d.num

if __name__ == '__main__':
    from Tkinter import Tk
    root = Tk()
    t = Button(root, text='Test', command=_test)
    t.pack()
    q = Button(root, text='Quit', command=t.quit)
    q.pack()
    t.mainloop()
