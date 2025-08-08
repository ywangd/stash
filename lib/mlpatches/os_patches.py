# -*- coding: utf-8 -*-
"""this module contains the patches for the os module."""

from mlpatches.base import FunctionPatch, PatchGroup

from mlpatches.os_process import getpid, getppid, kill

# define patches


class GetpidPatch(FunctionPatch):
    PY3 = True
    module = "os"
    function = "getpid"
    replacement = getpid


class GetppidPatch(FunctionPatch):
    PY3 = True
    module = "os"
    function = "getppid"
    replacement = getppid


class KillPatch(FunctionPatch):
    PY3 = True
    module = "os"
    function = "kill"
    replacement = kill


# create patch instances

GETPID_PATCH = GetpidPatch()
GETPPID_PATCH = GetppidPatch()
KILL_PATCH = KillPatch()

# define groups


class PopenPatches(PatchGroup):
    """all popen patches."""

    patches = []


class ProcessingPatches(PatchGroup):
    """all patches to emulate prcessing behavior"""

    patches = [
        GETPID_PATCH,
        GETPPID_PATCH,
        KILL_PATCH,
    ]


class OsPatches(PatchGroup):
    """all os patches."""

    patches = [
        GETPID_PATCH,
        GETPPID_PATCH,
        KILL_PATCH,
    ]


# create group instances

POPEN_PATCHES = PopenPatches()
OS_PATCHES = OsPatches()
PROCESSING_PATCHES = ProcessingPatches()
