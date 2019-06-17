"""
This package contains the UI for StaSh.
"""
import os

from stash.system.shcommon import IN_PYTHONISTA

# check if running on travis
ON_TRAVIS = "TRAVIS" in os.environ

# load best UI

found = False

if IN_PYTHONISTA:
    # load classic ui
    from .pythonista_ui import ShUI, ShTerminal
    found = True
elif ON_TRAVIS:
    # stub terminal
    from .stubui import ShUI, ShTerminal
    found = True
#else:
    ## attempt to import TkinterUI
    #try:
        #from .tkui import ShUI, ShTerminal
    #except ImportError as e:
        ## do nothing here
        #pass
    #else:
        #found = True



# raise Exception if no ui could be loaded
if not found:
    raise NotImplementedError("No UI implemented for the current system!")


__all__ = ["ShUI", "ShTerminal"]
