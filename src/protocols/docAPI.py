import urllib

def open_doc(url):
    if url[:1] != '/': url = '/' + url
    return urllib.urlopen("http://monty.cnri.reston.va.us/grail" + url)
