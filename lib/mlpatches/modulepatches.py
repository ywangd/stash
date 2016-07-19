"""this module contains a dictionary of all modulepatches."""
from mlpatches import base


class Popen2Patch(base.ModulePatch):
	"""the patch for the popen2 module."""
	PY2 = True
	PY3 = False
	relpath = "popen2"


# create instances
POPEN2PATCH = Popen2Patch()


# name -> ModulePatch()
MODULE_PATCHES = {
	"popen2": POPEN2PATCH,
}
