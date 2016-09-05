"""base functions and classes."""
from stashutils.fsi.errors import OperationFailure


class BaseFSI(object):
	"""
Baseclass for all FSIs.
Other FSIs should subclass this.
This class currently only serves as a documentation, but this may change.
"""
	def __init__(self, logger=None):
		"""called on __init__"""
		self.logger = logger
	
	def connect(self, *args):
		"""
Called to 'connect' to a filesystem.
'args' are the additional args passed by the user.
This should be no-op on if no connection nor setup is required.
This should return True on success, otherwise a string describing the error.
"""
		return "Not Implemented"

	def repr(self):
		"""
this should return a string identifying the instance of this interface.
"""
		return "Unknown Interface"

	def listdir(self):
		"""
called for listing a dir.
The FSI is responsible for keeping track of the cwd.
This should return a list of strings.
'..' doesnt need to be added.
"""
		return []

	def cd(self, name):
		"""this should change the cwd to name."""
		raise OperationFailure("NotImplemented")

	def get_path(self):
		"""this should return the current path as a string."""
		return "/"

	def remove(self, name):
		"""this should remove name. name may refer either to a dir or a file."""
		raise OperationFailure("NotImplemented")

	def open(self, name, mode):
		"""
		this should return a file-like object opened in mode mode.
		"""
		raise OperationFailure("NotImplemented")

	def mkdir(self, name):
		"""this should create a dir."""
		raise OperationFailure("NotImplemented")

	def close(self):
		"""this should close the interface.
		There is a chance that this may not be called."""
		pass

	def isdir(self, name):
		"""this should return True if name is an existing directory and
		False if not."""
		raise OperationFailure("NotImplemented")

	def isfile(self, name):
		"""this should return wether name is an existing file."""
		# default: not isdir(). problem: no exist check
		return not self.isdir(name)
	
	def log(self, msg):
		"""logs/prints a message to self.logger."""
		if self.logger is not None:
			self.logger(msg)