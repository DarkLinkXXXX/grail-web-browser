"""URI resolution context.

The use of 'url' in the method names is a historical accident.

"""
__version__ = '$Revision: 1.1 $'

from urlparse import urljoin


class URIContext:
    """URI resolution context."""

    def __init__(self, url="", baseurl=""):
        self.__url = url or ""
        if url and baseurl:
            self.__baseurl = urljoin(url, baseurl)
        else:
            self.__baserl = baseurl or ""

    def get_url(self):
        return self.__url

    def set_url(self, url, baseurl=None):
        """Set source URI and base URI for the current resource.

        The loaded URI is what this page was loaded from; the base URI
        is used to calculate relative links, and defaults to the
        loaded URI.

        """
        self.__url = url
        if baseurl:
            self.__baseurl = urljoin(url, baseurl)
        else:
            self.__baseurl = url

    def get_baseurl(self, *relurls):
        """Return the base URI for the current page, joined with relative URIs.

        Without arguments, return the base URI.
        
        With arguments, return the base URI joined with all of the
        arguments.  Empty arguments don't contribute.

        """
        url = self.__baseurl or self.__url
        for rel in relurls:
            if rel:
                url = urljoin(url, rel)
        return url

    def set_baseurl(self, baseurl):
        """Set the base URI for the current page.

        The base URI is taken relative to the existing base URI.

        """
        self.__baseurl = urljoin(self.__baseurl or self.__url, baseurl)