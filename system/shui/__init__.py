"""
This package contains the UI for StaSh.
"""
import os

from stash.system.shcommon import IN_PYTHONISTA

# check if running on GitHub Actions CI
ON_CI = "CI" in os.environ


def get_platform():
    """
    Return a string describing the UI implementation to use.
    :return: platform identifier
    :rtype: str
    """
    # platform specific UIs
    if IN_PYTHONISTA:
        return "pythonista"
    elif ON_CI:
        return "stub"

    # attempt to fall back to tkinter
    try:
        from six.moves import tkinter
    except ImportError:
        # can not import tkinter
        # ignore this case. If this executes successfully, it is handled in the 'else' clause
        pass
    else:
        return "tkinter"

    # this function has still not returned.
    # this means that all UIs tried above failed.
    # we raise an error in this case.
    raise NotImplementedError("There is no UI implemented for this platform. If you are on a PC, you may be able to fix this by installing tkinter.")
    


def get_ui_implementation(platform=None):
    """
    Return the classes implementing the UI for the platform.
    :param platform: identifier describing the platform to get the UI implementation for. Defaults to None, in which case it tries to find the best UI.
    :type platform: str
    :return: (ShUI, ShSequentialRenderer)
    :rtype: tuple of (stash.shui.base.ShBaseUI, stash.shui.base.ShBaseSequentialRenderer)
    """
    if platform is None:
        platform = get_platform()
    if platform == "pythonista":
        from .pythonista_ui import ShUI, ShTerminal, ShSequentialRenderer
        return (ShUI, ShSequentialRenderer)
    elif platform == "stub":
        from .stubui import ShUI, ShTerminal, ShSequentialRenderer
        return (ShUI, ShSequentialRenderer)
    elif platform == "tkinter":
        from .tkui import ShUI, ShTerminal, ShSequentialRenderer
        return (ShUI, ShSequentialRenderer)
    else:
        raise NotImplementedError("No UI implemented for platform {}!".format(repr(platform)))


__all__ = ["get_platform", "get_ui_implementation"]
