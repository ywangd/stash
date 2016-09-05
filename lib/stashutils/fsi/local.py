"""The FSI for the local filesystem."""
import os
import shutil

from stashutils.core import get_stash
from stashutils.fsi.base import BaseFSI
from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists

_stash = get_stash()


class LocalFSI(BaseFSI):
	"""A FSI for the local filesystem."""
	def __init__(self, logger=None):
		self.logger = logger
		self.path = os.getcwd()

	def connect(self, *args):
		return True  # no setup required; connect is allways successful

	def repr(self):
		return "Local Filesystem [CWD: {p}]".format(p=self.path)

	def listdir(self):
		try:
			return os.listdir(self.path)
		except Exception as e:
			raise OperationFailure(str(e))

	def cd(self, name):
		if name == "..":
			self.path = os.path.dirname(self.path)
			return
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif not os.path.isdir(ap):
			raise IsFile()
		else:
			self.path = ap

	def get_path(self):
		return self.path

	def remove(self, name):
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif os.path.isdir(ap):
			try:
				shutil.rmtree(ap)
			except Exception as e:
				raise OperationFailure(str(e))
		elif os.path.isfile(ap):
			try:
				os.remove(ap)
			except Exception as e:
				raise OperationFailure(str(e))
		else:
			raise OperationFailure("Unknown type")

	def open(self, name, mode):
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		if os.path.isdir(ap):
			raise IsDir()
		else:
			try:
				return open(ap, mode)
			except Exception as e:
				raise OperationFailure(str(e))

	def mkdir(self, name):
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		if os.path.exists(ap):
			raise AlreadyExists("Already exists")
		else:
			try:
				os.makedirs(ap)
			except Exception as e:
				raise OperationFailure(str(e))

	def close(self):
		pass

	def isdir(self, name):
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		return os.path.isdir(ap)

	def isfile(self, name):
		if os.path.isabs(name):
			ap = name
		else:
			ap = os.path.join(self.path, name)
		return os.path.isfile(ap)