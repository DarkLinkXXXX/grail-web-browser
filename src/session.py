# Copyright (c) CNRI 1996-1998, licensed under terms and conditions of
# license agreement obtained from handle "hdl:1895.22/1003",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.5/", or file "LICENSE".


"""Client-side session management support."""
__version__ = '$Revision: 2.3 $'

import socket
import string
import sys


class Session:
    def __init__(self, command=None, client=None):
        self.__master = None
        self.__windows = []
        #
        if command is None:
            command = [sys.executable]
            if __debug__:
                command.append("-O")
            command = command + sys.argv
            command = string.join(command)
        if client is None:
            hostname = socket.gethostname()
            client = socket.gethostbyaddr(socket.gethostbyname(hostname))[0]
        #
        self.set_command(command)
        self.set_client(client)

    def get_leader(self):
        return self.__master

    def set_command(self, command):
        self.__command = command
        for window in self.__windows:
            window.command(command)

    def set_client(self, client):
        self.__client = client
        for window in self.__windows:
            window.client(client)

    def add_window(self, window):
        self.__windows.append(window)
        if self.__master is None:
            self.__set_master()
        self.__master.group(window)

    def del_window(self, window):
        if window is self.__master:
            self.__master = None
        try: self.__windows.remove(window)
        except ValueError: pass
        if self.__windows and self.__master is None:
            self.__set_master()

    def __set_master(self):
        self.__master = self.__windows[0]
        self.__master.command(self.__command)
        self.__master.client(self.__client)
        for window in self.__windows:
            self.__master.group(window)
