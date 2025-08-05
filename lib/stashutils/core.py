# -*- coding: utf-8 -*-
"""core utilities for StaSh-scripts"""

import threading
import imp
import os

from stash.system import shthreads


def get_stash():
    """
    returns the currently active StaSh-instance.
    returns None if it can not be found.
    This is useful for modules.
    """
    if "_stash" in globals():
        return globals()["_stash"]
    for thr in threading.enumerate():
        if isinstance(thr, shthreads.ShBaseThread):
            ct = thr
            while not ct.is_top_level():
                ct = ct.parent
            return ct.parent.stash
    return None


def load_from_dir(dirpath, varname):
    """
    returns a list of all variables named 'varname' in .py files in a directofy 'dirname'.
    """
    if not os.path.isdir(dirpath):
        return []
    ret = []
    for fn in os.listdir(dirpath):
        fp = os.path.join(dirpath, fn)
        if not os.path.isfile(fp):
            continue
        with open(fp, "r") as fin:
            mod = imp.load_source(fn[: fn.index(".")], fp, fin)
        if not hasattr(mod, varname):
            continue
        else:
            ret.append(getattr(mod, varname))
    return ret
