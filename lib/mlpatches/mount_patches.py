"""This module contains the group definition for the mount patches."""
from mlpatches.base import PatchGroup
from mlpatches import mount_base

_BASE_PATCHES = filter(
	None,
	[
		getattr(mount_base, p) if p.endswith("PATCH") else None for p in dir(mount_base)
		]
	)


class MountPatches(PatchGroup):
	"""All mount patches."""
	patches = [
		
		] + _BASE_PATCHES


# create patchgroup instances
MOUNT_PATCHES = MountPatches()