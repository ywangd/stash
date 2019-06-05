# -*- coding: utf-8 -*-
"""this module contains the patches for the os module."""
from mlpatches.base import FunctionPatch, PatchGroup

from mlpatches.os_popen import popen, popen2, popen3, popen4, system
from mlpatches.os_process import getpid, getppid, kill


# define patches

class PopenPatch(FunctionPatch):
    PY2 = True
    PY3 = False
    module = "os"
    function = "popen"
    replacement = popen


class Popen2Patch(FunctionPatch):
    PY2 = True
    PY3 = False
    module = "os"
    function = "popen2"
    replacement = popen2


class Popen3Patch(FunctionPatch):
    PY2 = True
    PY3 = False
    module = "os"
    function = "popen3"
    replacement = popen3


class Popen4Patch(FunctionPatch):
    PY2 = True
    PY3 = False
    module = "os"
    function = "popen4"
    replacement = popen4


class SystemPatch(FunctionPatch):
    PY2 = True
    PY3 = False
    module = "os"
    function = "system"
    replacement = system


class GetpidPatch(FunctionPatch):
    PY2 = True
    PY3 = True
    module = "os"
    function = "getpid"
    replacement = getpid


class GetppidPatch(FunctionPatch):
    PY2 = True
    PY3 = True
    module = "os"
    function = "getppid"
    replacement = getppid


class KillPatch(FunctionPatch):
    PY2 = True
    PY3 = True
    module = "os"
    function = "kill"
    replacement = kill


# create patch instances

POPEN_PATCH = PopenPatch()
POPEN2_PATCH = Popen2Patch()
POPEN3_PATCH = Popen3Patch()
POPEN4_PATCH = Popen4Patch()

SYSTEM_PATCH = SystemPatch()

GETPID_PATCH = GetpidPatch()
GETPPID_PATCH = GetppidPatch()
KILL_PATCH = KillPatch()


# define groups

class PopenPatches(PatchGroup):
    """all popen patches."""
    patches = [
        POPEN_PATCH,
        POPEN2_PATCH,
        POPEN3_PATCH,
        POPEN4_PATCH,
    ]


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
        POPEN_PATCH,
        POPEN2_PATCH,
        POPEN3_PATCH,
        POPEN4_PATCH,
        SYSTEM_PATCH,
        GETPID_PATCH,
        GETPPID_PATCH,
        KILL_PATCH,
    ]


# create group instances

POPEN_PATCHES = PopenPatches()
OS_PATCHES = OsPatches()
PROCESSING_PATCHES = ProcessingPatches()
