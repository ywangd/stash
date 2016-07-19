"""This module contains a dictionary containing all patches and their name."""

from mlpatches import base, os_patches, modulepatches

PATCHES = {  # name -> Patch()
	"os_popen": os_patches.POPEN_PATCH,
	"os_popen2": os_patches.POPEN2_PATCH,
	"os_popen3": os_patches.POPEN3_PATCH,
	"os_popen4": os_patches.POPEN4_PATCH,
	"os_system": os_patches.SYSTEM_PATCH,
	"OS_POPEN": os_patches.POPEN_PATCHES,
	"OS": os_patches.OS_PATCHES,
	
}


# update with modulepatches

PATCHES.update(modulepatches.MODULE_PATCHES)


# define a PatchGroup with all patches

class AllPatches(base.PatchGroup):
	"""a patch-group containing all patches."""
	patches = PATCHES.values()

ALL_PATCHES = AllPatches()
PATCHES["ALL"] = ALL_PATCHES
