"""This module contains the group definition for the mount patches."""
from mlpatches.base import PatchGroup
from mlpatches import mount_base
from stashutils import mount_ctrl

_BASE_PATCHES = list(filter(
	None,
	[
		getattr(mount_base, p) if p.endswith("PATCH") else None for p in dir(mount_base)
		]
	))


class MountPatches(PatchGroup):
	"""All mount patches."""
	patches = [
		
		] + _BASE_PATCHES
	
	def pre_enable(self):
		# ensure a manager is set
		manager = mount_ctrl.get_manager()
		if manager is None:
			from stashutils import mount_manager  # import here to prevent an error
			manager = mount_manager.MountManager()
			mount_ctrl.set_manager(manager)


# create patchgroup instances
MOUNT_PATCHES = MountPatches()