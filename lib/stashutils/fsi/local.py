"""The FSI for the local filesystem."""
import os
import shutil

from stashutils.core import get_stash
from stashutils.fsi.base import BaseFSI
from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists

from mlpatches.mount_base import _org_stat, _org_listdir, _org_mkdir
from mlpatches.mount_base import _org_open, _org_remove

_stash = get_stash()


class LocalFSI(BaseFSI):
	"""A FSI for the local filesystem."""
	def __init__(self, logger=None):
		self.logger = logger
		self.path = os.getcwd()
	
	def _getabs(self, name):
		"""returns the path for name."""
		path = os.path.join(self.path, name)
		while path.startswith("/"):
			path = path[1:]
		return os.path.abspath(
			os.path.join(self.basepath, path)
			)

	def connect(self, *args):
		if len(args) == 0:
			self.basepath = "/"
			return True  # no setup required; connect is allways successful
		else:
			self.basepath = args[0]
			if not os.path.isdir(self.basepath):
				return "No such directory: {p}".format(p=self.basepath)
			return True

	def repr(self):
		return "Local Directory '{bp}' [CWD: {p}]".format(
			p=self.path, bp=self.basepath
			)

	def listdir(self, path="."):
		ap = self._getabs(path)
		try:
			return _org_listdir(ap)
		except Exception as e:
			raise OperationFailure(str(e))

	def cd(self, name):
		if name == "..":
			self.path = os.path.abspath(os.path.dirname(self.path))
			return
		ap = self._getabs(name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif not os.path.isdir(ap):
			raise IsFile()
		else:
			self.path = ap

	def get_path(self):
		return self.path

	def remove(self, name):
		ap = self._getabs(name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif os.path.isdir(ap):
			try:
				shutil.rmtree(ap)
			except Exception as e:
				raise OperationFailure(str(e))
		elif os.path.isfile(ap):
			try:
				_org_remove(ap)
			except Exception as e:
				raise OperationFailure(str(e))
		else:
			raise OperationFailure("Unknown type")

	def open(self, name, mode, buffering=0):
		ap = self._getabs(name)
		if os.path.isdir(ap):
			raise IsDir()
		else:
			try:
				return _org_open(ap, mode, buffering)
			except Exception as e:
				raise OperationFailure(str(e))

	def mkdir(self, name):
		ap = self._getabs(name)
		if os.path.exists(ap):
			raise AlreadyExists("Already exists")
		else:
			try:
				_org_mkdir(ap)
			except Exception as e:
				raise OperationFailure(str(e))

	def close(self):
		pass

	def isdir(self, name):
		ap = self._getabs(name)
		return os.path.isdir(ap)

	def isfile(self, name):
		ap = self._getabs(name)
		return os.path.isdir(ap)
	
	def stat(self, name):
		ap = self._getabs(name)
		return _org_stat(ap)