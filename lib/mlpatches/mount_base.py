# -*- coding: utf-8 -*-
"""base patches for mount."""
import os
import stat as _stat

from six import text_type
from six.moves import builtins

from mlpatches import base

from stashutils.mount_ctrl import get_manager
from stashutils.fsi.errors import IsFile, OperationFailure


# store default functions

_org_listdir = os.listdir
_org_open = builtins.open
_org_chdir = os.chdir
_org_getcwd = os.getcwd
_org_ismount = os.path.ismount
_org_stat = os.stat
_org_lstat = os.lstat
_org_mkdir = os.mkdir
_org_remove = os.remove
_org_rmdir = os.rmdir
_org_access = os.access
_org_chmod = os.chmod


def listdir(patch, path):
	"""
	Return a list containing the names of the entries in the directory
	given by path. The list is in arbitrary order.
	It does not include the special entries '.' and '..' even if
	they are present in the directory.
	"""
	ap = os.path.abspath(os.path.join(os.getcwd(), path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_listdir(ap)
	else:
		try:
			return fsi.listdir(relpath)
		except OperationFailure:
			raise os.error(
				"[Errno 2] No such file or directory: '/{p}'".format(
					p=ap
					)
				)


def open(patch, name, mode="r", buffering=0):
	"""
	Open a file, returning an object of the file type described in section
	File Objects.
	If the file cannot be opened, IOError is raised.
	When opening a file, its preferable to use open() instead of invoking
	the file constructor directly.
	"""
	path = os.path.abspath(os.path.join(os.getcwd(), name))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(path)
	if fsi is None:
		return _org_open(relpath, mode, buffering)
	elif (("w" in mode) or ("a" in mode) or ("+" in mode)) and readonly:
		raise IOError(
			"[Errno 1] Operation not permitted: '{p}'".format(
				p=path
				)
			)
	else:
		try:
			return fsi.open(relpath, mode, buffering)
		except OperationFailure:
			raise os.error(
				"[Errno 2] No such file or directory: '{p}'".format(
					p=path
					)
				)


CWD = _org_getcwd()  # constant storing the cwd


def getcwd(patch):
	"""Return a string representing the current working directory."""
	return CWD


def getcwdu(patch):
	"""Return a Unicode object representing the current working directory."""
	return text_type(CWD)


def chdir(patch, path):
	"""Change the current working directory to path."""
	global CWD
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		if not os.path.exists(ap):
			raise os.error(
				"[Errno 2] No such file or directory: '/{p}/'".format(
					p=path
					)
				)
		elif not os.path.isdir(ap):
			raise os.error(
				"[Errno 20] Not a directory: '{p}'".format(
					p=path
					)
				)
		else:
			CWD = ap
			_org_chdir(ap)
			# reset paths
			for p, fs, readonly in manager.get_mounts():
				try:
					fs.cd("/")
				except:
					pass
	else:
		try:
			fsi.cd(relpath)
			CWD = ap
		except IsFile:
			raise os.error(
				"[Errno 20] Not a directory: '{p}'".format(
					p=path
					)
				)
		except OperationFailure:
			raise os.error(
				"[Errno 2] No such file or directory: '/{p}/'".format(
					p=path
					)
				)


def ismount(patch, path):
	"""
	Return True if pathname path is a mount point:
	a point in a file system where a different file system has been mounted.
	The function checks whether path's parent, path/..,
	is on a different device than path,
	or whether path/.. and path point to the same i-node on the same device
	- this should detect mount points for all Unix and POSIX variants."""
	# ^^^ orginal docstring. we can simply ask the manager :)
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_ismount(ap)
	else:
		return True


def stat(patch, path):
	"""
	Perform the equivalent of a stat() system call on the given path.
	(This function follows symlinks; to stat a symlink use lstat().)
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_stat(relpath)
	else:
		try:
			return fsi.stat(relpath)
		except OperationFailure:
			raise os.error(
				"[Errno 2] No such file or directory: '{p}'".format(
					p=ap
					)
				)


def lstat(patch, path):
	"""
	Perform the equivalent of an lstat() system call on the given path.
	Similar to stat(), but does not follow symbolic links.
	On platforms that do not support symbolic links, this is an alias for stat().
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_lstat(relpath)
	else:
		# we dont have 'lstat', fallback to stat()
		try:
			return fsi.stat(relpath)
		except OperationFailure:
			raise os.error(
				"[Errno 2] No such file or directory: '{p}'".format(
					p=ap
					)
				)


def mkdir(patch, path, mode=0o777):
	"""
	Create a directory named path with numeric mode mode.
	The default mode is 0777 (octal). On some systems, mode is ignored.
	Where it is used, the current umask value is first masked out.
	If the directory already exists, OSError is raised.
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_mkdir(relpath, mode)
	elif readonly:
		raise IOError(
			"[Errno 1] Operation not permitted: '{p}'".format(
				p=ap
				)
			)
	else:
		# FSI.mkdir() doesnt have a 'mode' argument, we need to ignore this
		try:
			return fsi.mkdir(relpath)
		except OperationFailure as e:
			raise os.error(e.message)


def remove(patch, path):
	"""
	Remove (delete) the file path.
	If path is a directory, OSError is raised; see rmdir() below to remove
	a directory.
	This is identical to the unlink() function documented below.
	On Windows, attempting to remove a file that is in use causes an
	exception to be raised; on Unix, the directory entry is removed but the
	storage allocated to the file is not made available until the original
	file is no longer in use.
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_remove(relpath)
	elif readonly:
		raise IOError(
			"[Errno 1] Operation not permitted: '{p}'".format(
				p=ap
				)
			)
	else:
		# FSI.remove() works on both files and dirs, we need to check
		# this before and raise an Exception if required
		if os.path.isdir(relpath):
			raise os.error(
				"OSError: [Errno 21] Is a directory: '{p}'".format(p=ap)
				)
		try:
			return fsi.remove(relpath)
		except OperationFailure as e:
			raise os.error(e.message)


def rmdir(patch, path):
	"""
	Remove (delete) the directory path.
	Only works when the directory is empty, otherwise, OSError is raised.
	In order to remove whole directory trees, shutil.rmtree() can be used.
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_rmdir(relpath)
	elif readonly:
		raise IOError(
			"[Errno 1] Operation not permitted: '{p}'".format(
				p=ap
				)
			)
	else:
		# FSI.remove() works on both files and dirs.
		if os.path.isfile(relpath):
			raise os.error(
				"[Errno 20] Not a directory: '{p}'".format(p=ap)
				)
		try:
			return fsi.remove(relpath)
		except OperationFailure as e:
			raise os.error(e.message)


def access(patch, path, mode):
	"""
	Use the real uid/gid to test for access to path.
	Note that most operations will use the effective uid/gid,
	therefore this routine can be used in a suid/sgid environment to test
	if the invoking user has the specified access to path.
	mode should be F_OK to test the existence of path,
	or it can be the inclusive OR of one or more of R_OK, W_OK, and X_OK to
	test permissions. Return True if access is allowed, False if not.
	See the Unix man page access(2) for more information.
	"""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_access(relpath, mode)
	else:
		try:
			s = fsi.stat(relpath)
		except OperationFailure:
			return False
		if mode == os.F_OK:
			return True
		fa_mode = s.st_mode #  & 0777
		should_read = mode & os.R_OK
		should_write = mode & os.W_OK
		should_exec = mode & os.X_OK
		acc = True
		if should_read:
			acc = acc and any((
				_stat.S_IRUSR & fa_mode,
				_stat.S_IRGRP & fa_mode,
				_stat.S_IROTH & fa_mode,
				))
		if should_write:
			acc = acc and any((
				_stat.S_IWUSR & fa_mode,
				_stat.S_IWGRP & fa_mode,
				_stat.S_IWOTH & fa_mode,
				))
			acc = (acc and (not readonly))
		if should_exec:
			acc = acc and any((
				_stat.S_IXUSR & fa_mode,
				_stat.S_IXGRP & fa_mode,
				_stat.S_IXOTH & fa_mode,
				))
		return acc


def chmod(patch, path, mode):
	"""Change the mode of path to the numeric mode."""
	ap = os.path.abspath(os.path.join(CWD, path))
	manager = get_manager()
	fsi, relpath, readonly = manager.get_fsi(ap)
	if fsi is None:
		return _org_chmod(relpath, mode)
	elif readonly:
		raise IOError(
			"[Errno 1] Operation not permitted: '{p}'".format(
				p=ap
				)
			)
	else:
		# we cant do this
		pass
		

# define patches

class ListdirPatch(base.FunctionPatch):
	"""patch for os.listdir()"""
	module = "os"
	function = "listdir"
	replacement = listdir


class Py2OpenPatch(base.FunctionPatch):
	"""patch for builtins.open()"""
	PY3 = base.SKIP
	module = "__builtin__"
	function = "open"
	replacement = open


class Py3OpenPatch(base.FunctionPatch):
	"""patch for builtins.open()"""
	PY2 = base.SKIP
	module = "builtins"
	function = "open"
	replacement = open


class SixOpenPatch(base.FunctionPatch):
	"""patch for builtins.open()"""
	module = "six.moves.builtins"
	function = "open"
	replacement = open


class Py2GetcwdPatch(base.FunctionPatch):
	"""patch for os.getcwd()"""
	PY3 = base.SKIP
	module = "os"
	function = "getcwd"
	replacement = getcwd


class Py3GetcwdPatch(base.FunctionPatch):
	"""patch for os.getcwd()"""
	PY2 = base.SKIP
	module = "os"
	function = "getcwd"
	replacement = getcwdu


class Py2GetcwduPatch(base.FunctionPatch):
	"""patch for os.getcwdu()"""
	PY3 = base.SKIP
	module = "os"
	function = "getcwdu"
	replacement = getcwdu


class Py3GetcwdbPatch(base.FunctionPatch):
	"""patch for os.getcwd()"""
	PY2 = base.SKIP
	module = "os"
	function = "getcwdb"
	replacement = getcwd


class ChdirPatch(base.FunctionPatch):
	"""patch for os.chdir()."""
	module = "os"
	function = "chdir"
	replacement = chdir


class IsmountPatch(base.FunctionPatch):
	"""patch for os.ismount()."""
	module = "os.path"
	function = "ismount"
	replacement = ismount


class StatPatch(base.FunctionPatch):
	"""patch for os.stat()"""
	module = "os"
	function = "stat"
	replacement = stat


class LstatPatch(base.FunctionPatch):
	"""patch for os.lstat()"""
	module = "os"
	function = "lstat"
	replacement = lstat


class MkdirPatch(base.FunctionPatch):
	"""patch for os.mkdir()"""
	module = "os"
	function = "mkdir"
	replacement = mkdir


class RemovePatch(base.FunctionPatch):
	"""patch for os.remove()"""
	module = "os"
	function = "remove"
	replacement = remove


class RmdirPatch(base.FunctionPatch):
	"""patch for os.rmdir()"""
	module = "os"
	function = "rmdir"
	replacement = rmdir


class AccessPatch(base.FunctionPatch):
	"""patch for os.access"""
	module = "os"
	function = "access"
	replacement = access


class ChmodPatch(base.FunctionPatch):
	"""patch for os.chmod"""
	module = "os"
	function = "chmod"
	replacement = chmod


# create patch instances

LISTDIR_PATCH = ListdirPatch()

PY2_OPEN_PATCH = Py2OpenPatch()
PY3_OPEN_PATCH = Py3OpenPatch()
SIX_OPEN_PATCH = SixOpenPatch()

PY2_GETCWD_PATCH = Py2GetcwdPatch()
PY3_GETCWD_PATCH = Py3GetcwdPatch()
PY2_GETCWDU_PATCH = Py2GetcwduPatch()
PY3_GETCWDB_PATCH = Py3GetcwdbPatch()

CHDIR_PATCH = ChdirPatch()
ISMOUNT_PATCH = IsmountPatch()
STAT_PATCH = StatPatch()
LSTAT_PATCH = LstatPatch()
MKDIR_PATCH = MkdirPatch()
REMOVE_PATCH = RemovePatch()
RMDIR_PATCH = RmdirPatch()
ACCESS_PATCH = AccessPatch()
CHMOD_PATCH = ChmodPatch()