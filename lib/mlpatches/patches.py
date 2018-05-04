"""This module contains a dictionary containing all patches and their name."""
from stash.system.shcommon import _STASH_EXTENSION_PATCH_PATH

from stashutils.core import load_from_dir

from mlpatches import base, os_patches, modulepatches, tl_patches
from mlpatches import mount_patches

STABLE_PATCHES = {  # name -> Patch()
	"os_popen": os_patches.POPEN_PATCH,
	"os_popen2": os_patches.POPEN2_PATCH,
	"os_popen3": os_patches.POPEN3_PATCH,
	"os_popen4": os_patches.POPEN4_PATCH,
	"os_system": os_patches.SYSTEM_PATCH,
	"os_getpid": os_patches.GETPID_PATCH,
	"os_getppid": os_patches.GETPPID_PATCH,
	"os_kill": os_patches.KILL_PATCH,
	"OS_POPEN": os_patches.POPEN_PATCHES,
	"OS_PROCESSING": os_patches.PROCESSING_PATCHES,
	"OS": os_patches.OS_PATCHES,
}

INSTABLE_PATCHES = {  # name -> Patch()
	# "tl_argv": tl_patches.TL_ARGV_PATCH,
	"MOUNT": mount_patches.MOUNT_PATCHES,
}

# update with extensions
extensions = load_from_dir(
	dirpath=_STASH_EXTENSION_PATCH_PATH, varname="STABLE_PATCHES",
	)
for ext in extensions:
	if not isinstance(ext, dict):
		continue
	else:
		STABLE_PATCHES.update(ext)

extensions = load_from_dir(
	dirpath=_STASH_EXTENSION_PATCH_PATH, varname="INSTABLE_PATCHES",
	)
for ext in extensions:
	if not isinstance(ext, dict):
		continue
	else:
		INSTABLE_PATCHES.update(ext)

# create an empty dict and update it

PATCHES = {}

STABLE_PATCHES.update(modulepatches.MODULE_PATCHES)  # modulepatches should be available in STABLE
PATCHES.update(INSTABLE_PATCHES)  # update with INSTABLE first
PATCHES.update(STABLE_PATCHES)  # update with STABLE patches (overwriting INSTABLE patches if required)


# define a PatchGroup with all patches
STABLE_GROUP = base.VariablePatchGroup(list(STABLE_PATCHES.values()))
INSTABLE_GROUP = base.VariablePatchGroup(list(INSTABLE_PATCHES.values()))
ALL_GROUP = base.VariablePatchGroup(list(PATCHES.values()))


PATCHES["ALL"] = ALL_GROUP
PATCHES["STABLE"] = STABLE_GROUP
PATCHES["INSTABLE"] = INSTABLE_GROUP