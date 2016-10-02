"""helper functions and base classes."""
from stashutils.fsi.errors import OperationFailure
import random
import os
import time
import stat
import pwd


class BaseFSI(object):
	"""
Baseclass for all FSIs.
Other FSIs should subclass this.
This class currently only serves as a documentation, but this may change.
"""
	def __init__(self, logger=None):
		"""
		called on __init__().
		"logger" should be a callable,
		which will be called with log messages, or None.
		"""
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

	def listdir(self, path="."):
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

	def open(self, name, mode="r", buffering=0):
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
	
	def stat(self, name):
		"""
		this should stat the file name and return a os.stat_result or
		FakeStatResult().
		"""
		if self.isfile(name):
			return make_stat(type=stat.S_IFREG)
		else:
			return make_stat(type=stat.S_IFDIR)
		
	
	def log(self, msg):
		"""logs/prints a message to self.logger."""
		if self.logger is not None:
			self.logger(msg)


def calc_mode(
	sticky=False,
	isuid=True,
	isgid=True,
	type=stat.S_IFREG,
	owner_read=True,
	owner_write=True,
	owner_exec=True,
	group_read=True,
	group_write=True,
	group_exec=True,
	other_read=True,
	other_write=True,
	other_exec=True,
	):
	"""helper function to calculate the mode bits of a file."""
	mode = 0
	if owner_read:
		mode |= stat.S_IRUSR
	if owner_write:
		mode |= stat.S_IWUSR
	if owner_exec:
		mode |= stat.S_IXUSR
	if group_read:
		mode |= stat.S_IRGRP
	if group_write:
		mode |= stat.S_IWGRP
	if group_exec:
		mode |= stat.S_IXGRP
	if other_read:
		mode |= stat.S_IROTH
	if other_write:
		mode |= stat.S_IWOTH
	if other_exec:
		mode |= stat.S_IXOTH
	if sticky:
		mode |= stat.S_ISVTX
	if isuid:
		mode |= stat.ST_UID
	if isgid:
		mode |= stat.ST_GID
	mode |= type
	return mode


DEFAULT_MODE = calc_mode()


def make_stat(
	mode=DEFAULT_MODE,
	inode=None,
	dev=None,
	nlinks=1,
	gid=None,
	uid=None,
	size=0,
	atime=None,
	mtime=None,
	ctime=None,
	blocks=1,
	blksize=None,
	rdev=stat.S_IFREG,
	flags=0,
	):
	"""helper function to generate os.stat results."""
	if inode is None:
		inode = random.randint(1000, 9999999)
	if dev is None:
		dev = os.makedev(64, random.randint(1, 100))
	if uid is None:
		uid = os.getuid()
	if gid is None:
		uid2 = os.getuid()
		gid = pwd.getpwuid(uid2).pw_gid
	if atime is None:
		atime = time.time()
	if mtime is None:
		mtime = time.time()
	if ctime is None:
		ctime = time.time()
	if os.stat_float_times():
		ctime = float(ctime)
		mtime = float(mtime)
		atime = float(atime)
	else:
		ctime = int(ctime)
		atime = int(atime)
		mtime = int(mtime)
	if blksize is None:
		blksize = max(size, 2048)
	s = os.stat_result(
		(
			mode,
			inode,
			dev,
			nlinks,
			gid,
			uid,
			size,
			atime,
			mtime,
			ctime,
			),
		{
			"st_blocks": blocks,
			"st_blksize": blksize,
			"st_rdev": rdev,
			"st_flags": flags,
			}
		)
	return s