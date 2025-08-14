# -*- coding: utf-8 -*-
"""this module contains a dictionary of all modulepatches."""

from mlpatches import base


class Popen2Patch(base.ModulePatch):
    """the patch for the popen2 module."""

    PY3 = False
    relpath = "popen2.py"
    name = "popen2"


class SubprocessPatch(base.ModulePatch):
    """the patch for the subprocess module."""

    PY3 = False  # uses unicode
    relpath = "subprocess.py"
    name = "subprocess"


# create instances
POPEN2PATCH = Popen2Patch()
SUBPROCESSPATCH = SubprocessPatch()

# name -> ModulePatch()
MODULE_PATCHES = {
    "popen2": POPEN2PATCH,
    "subprocess": SUBPROCESSPATCH,
}
