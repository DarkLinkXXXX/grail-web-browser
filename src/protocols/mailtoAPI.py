# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:cnri/19980302135001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.4/", or file "LICENSE".

"""mailto: URI scheme handler."""

import grailutil

from nullAPI import null_access

from MailDialog import MailDialog


class mailto_access(null_access):

    def __init__(self, url, method, params, data=None):
        null_access.__init__(self, url, method, params)
        # when a form's action is a mail URL, the data field will be
        # non-None.  In that case, initialize the dialog with the data
        # contents
        toplevel = MailDialog(grailutil.get_grailapp().root, url, data)
