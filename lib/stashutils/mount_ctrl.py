"""
This module keeps track of the current MountManager.
This can not be done in stashutils.mount_manager, because this would create some import problems.
"""

# global: current mount manager

MANAGER = None


def get_manager():
	"""
	returns the current mount manager.
	Use the function instead of the constant to prevent import problems/
	"""
	return MANAGER


def set_manager(manager):
	"""sets the current manager."""
	global MANAGER
	MANAGER = manager