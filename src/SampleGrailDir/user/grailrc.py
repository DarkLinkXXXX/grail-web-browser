# Copyright (c) CNRI 1996, licensed under terms and conditions of license
# agreement obtained from handle "hdl:CNRI/19970131120001",
# URL "http://grail.cnri.reston.va.us/LICENSE-0.3/", or file "LICENSE".

# Grail initialization file

# Turn on remote control.  Ignore error that get's raised if some
# other Grail is being remote controlled.
import RemoteControl
RemoteControl.register_loads()
try:
    RemoteControl.start()
except RemoteControl.ClashError:
    pass
