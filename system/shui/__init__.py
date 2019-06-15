"""
This package contains the UI for StaSh.
"""
from stash.system.shcommon import IN_PYTHONISTA


# load best UI

found = False

if IN_PYTHONISTA:
    # load classic ui
    from .pythonista_ui import ShUI
    found = True
else:
    # attempt to import TkinterUI
    try:
        from .tkui import ShUI
    except ImportError as e:
        # do nothing here
        pass
    else:
        found = True


# raise Exception if no ui could be loaded
if not found:
    raise NotImplementedError("No UI implemented for the current system!")

__all__ = ["ShUI"]
