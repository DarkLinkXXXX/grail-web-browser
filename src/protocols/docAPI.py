"""doc: URL scheme handler."""

def open_doc(parturl):
    if parturl[:1] != '/': parturl = '/' + parturl
    newurl = "http://monty.cnri.reston.va.us/grail" + parturl
    raise IOError, ('redirect error', 302, 'Moved', {'location': newurl})
