"""this module contains the patches for the os module."""
from mlpatches.base import FunctionPatch, PatchGroup

from mlpatches.os_popen import popen, popen2, popen3, popen4


# define patches

class PopenPatch(FunctionPatch):
	module = "os"
	function = "popen"
	replacement = popen


class Popen2Patch(FunctionPatch):
	module = "os"
	function = "popen2"
	replacement = popen2


class Popen3Patch(FunctionPatch):
	module = "os"
	function = "popen3"
	replacement = popen3


class Popen4Patch(FunctionPatch):
	module = "os"
	function = "popen4"
	replacement = popen4


# create patch instances

POPEN_PATCH = PopenPatch()
POPEN2_PATCH = Popen2Patch()
POPEN3_PATCH = Popen3Patch()
POPEN4_PATCH = Popen4Patch()


# define groups

class PopenPatches(PatchGroup):
	"""all popen patches."""
	patches = [POPEN_PATCH, POPEN2_PATCH, POPEN3_PATCH, POPEN4_PATCH]


# create group instances

POPEN_PATCHES = PopenPatches()
