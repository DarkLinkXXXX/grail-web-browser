"""doc: URL scheme handler."""

import urllib

def open_doc(parturl):
    if parturl[:1] != '/': parturl = '/' + parturl
    return urllib.urlopen("http://monty.cnri.reston.va.us/grail" + parturl)
