"""This module coordinates the mount-system."""
import os

from six import string_types

from mlpatches.mount_patches import MOUNT_PATCHES
from stashutils.core import get_stash
from stashutils.fsi.base import BaseFSI
from stashutils.fsi.errors import OperationFailure
from stashutils.mount_ctrl import get_manager, set_manager

_stash = get_stash()


# Exceptions

class MountError(Exception):
	"""raised when a mount failed."""
	pass


# the manager

class MountManager(object):
	"""
	this class keeps track of the FSIs and their position in the filesystem.
	"""
	def __init__(self):
		self.path2fs = {}
	
	def check_patches_enabled(self):
		"""checks wether all required patches are enabled."""
		return MOUNT_PATCHES.enabled
	
	def enable_patches(self):
		"""enables all patches required for mount."""
		if self.check_patches_enabled():
			return
		MOUNT_PATCHES.enable()
	
	def disable_patches(self):
		"""disables all required patches."""
		MOUNT_PATCHES.disable()
	
	def get_fsi(self, path):
		"""
		returns a tuple of (fsi, relpath) if path is on a mountpoint.
		otherwise, return (None, path).
		fsi is a FSI which should be used for the action.
		relpath is a path which should be used as the path for FSI actions.
		"""
		path = os.path.abspath(path)
		i = None
		for p in self.path2fs:
			if path.startswith(p):
				i, readonly = self.path2fs[p]
				relpath = path.replace(p, "", 1)
				if not relpath.startswith("/"):
					relpath = "/" + relpath
				return (i, relpath, readonly)
		return (None, path, False)
	
	def mount_fsi(self, path, fsi, readonly=False):
		"""mounts a fsi to a path."""
		if not isinstance(fsi, BaseFSI):
			raise ValueError("Expected a FSI!")
		if not isinstance(path, string_types):
			raise ValueError("Expected a string or unicode!")
		path = os.path.abspath(path)
		if path in self.path2fs:
			raise MountError("A Filesystem is already mounted on '{p}'!".format(p=path))
		elif not (os.path.exists(path) and os.path.isdir(path)):
			raise MountError("Path does not exists.")
		self.path2fs[path] = (fsi, readonly)
	
	def unmount_fsi(self, path, force=False):
		"""unmounts a fsi."""
		path = os.path.abspath(path)
		if not path in self.path2fs:
			raise MountError("Nothing mounted there.")
		fsi, readonly = self.path2fs[path]
		if not force:
			try:
				fsi.close()
			except OperationFailure as e:
				raise MountError(e.message)
		del self.path2fs[path]  # todo: close files
	
	def get_mounts(self):
		"""
		returns a list of (path, fsi, readonly) containing all currently
		mounted filesystems.
		"""
		ret = []
		for p in self.path2fs:
			fs, readonly = self.path2fs[p]
			ret.append((p,fs, readonly))
		return ret

# install manager

if get_manager() is None:
	set_manager(MountManager())
