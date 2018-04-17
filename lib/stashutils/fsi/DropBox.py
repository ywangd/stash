"""The FSI for dropbox."""
# this module is named 'DropBox' instead of 'dropbox' to avoid a
# naming conflict.
import os
import logging
import stat
import tempfile

import dropbox

from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists
from stashutils.fsi.base import BaseFSI, make_stat, calc_mode
from stashutils.dbutils import get_dropbox_client


# turn down requests log verbosity
logging.getLogger('requests').setLevel(logging.CRITICAL)

OVERWRITE = dropbox.files.WriteMode("overwrite", None)


class DropboxFSI(BaseFSI):
	"""A FSI for accessing dropbox."""
	def __init__(self, logger):
		self.logger = logger
		self.path = "/"
		self.client = None
	
	def abspath(self, path):
		"""returns thr absolute path for path."""
		p = os.path.join(self.path, path)
		if p == "/":
			return ""
		else:
			return p

	def connect(self, *args):
		"""connects to the dropbox. args[0] is the username."""
		if len(args) != 1:
			return "expected one argument!"
		try:
			dbci = get_dropbox_client(
				args[0], False, None, None
				)
		except Exception as e:
			return e.message
		else:
			if dbci is None:
				return "No Dropbox configured for '{u}'.".format(u=args[0])
			else:
				self.client = dbci
			return True

	def get_path(self):
		return self.path

	def repr(self):
		return "Dropbox [CWD: {p}]".format(p=self.path)

	def close(self):
		pass

	def cd(self, name):
		path = self.abspath(name)
		if name == "..":
			self.path = "/".join(self.path.split("/")[:-1])
			if self.path == "":
				self.path = "/"
			return
		try:
			# test
			self.client.files_list_folder(path, recursive=False)
		except dropbox.exceptions.ApiError as api_e:
			e = api_e.reason
			if e.is_other():
				raise OperationFailure(repr(e))
			elif e.is_path():
				pe = e.get_path()
				if pe.is_not_folder():
					raise IsFile()
				elif pe.is_not_found():
					raise OperationFailure("Not Found!")
				else:
					raise OperationFailure(repr(e))
			else:
				raise OperationFailure("Not found!")
		else:
			self.path = path

	def listdir(self, path="."):
		p = self.abspath(path)
		e = []
		try:
			c = self.client.files_list_folder(p, recursive=False)
			e += c.entries
			while True:
				if c.has_more:
					c = self.client.files_list_folder_continue(p)
					e += c.entries
				else:
					break
		except dropbox.exceptions.ApiError as e:
			raise OperationFailure(e.message)
		return [str(m.name) for m in e]
		
	def mkdir(self, name):
		path = self.abspath(name)
		try:
			self.client.files_create_folder(path)
		except dropbox.exceptions.ApiError as api_e:
			e = api_e.reason
			if e.is_path():
				pe = e.get_path()
				if pe.is_conflict():
					raise AlreadyExists("Already exists!")
				elif pe.is_insufficient_space():
					raise OperationFailure("Not enough Space available!")
				elif pe.is_disallowed_name():
					raise OperationFailure("Disallowed name!")
				elif pe.is_no_write_permission():
					raise OperationFailure("Permission denied!")
				else:
					raise OperationFailure(api_e.message)
			else:
				raise OperationFailure("Can not create dir!")

	def remove(self, name):
		path = self.abspath(name)
		try:
			self.client.files_delete(path)
		except dropbox.exceptions.ApiError:
			raise OperationFailure("Can not delete target!")

	def isdir(self, name):
		path = self.abspath(name)
		try:
			self.client.files_list_folder(path, recursive=False)
			return True
		except dropbox.exceptions.ApiError:
			return False

	def isfile(self, name):
		return not self.isdir(name)

	def open(self, name, mode="rb", buffering=0):
		mode = mode.replace("+", "")
		ap = self.abspath(name)
		if mode in ("r", "rb", "rU"):
			try:
				response = self.client.files_download(ap)[1]
				# unfortunaly, we cant return response.raw because it does not
				# support seek(), which is required by tarfile (used in ls)
				return Dropbox_Download(
					self.client, name, mode, buffering, response,
					)
			except dropbox.exceptions.ApiError as api_e:
				e = api_e.reason
				if e.is_path():
					pe = e.get_path()
					if pe.is_not_file():
						raise IsDir()
				raise OperationFailure(api_e.message)
		elif "w" in mode:
			return Dropbox_Upload(self.client, ap, mode)
		else:
			raise OperationFailure("Mode not supported!")
	
	def stat(self, name):
		ap = self.abspath(name)
		if ap in ("/", "/.", "./", "//", ""):
			bytes = 0
			isdir = True
		else:
			try:
				meta = self.client.files_get_metadata(ap)
			except dropbox.exceptions.ApiError as e:
				raise OperationFailure(e.message)
			if isinstance(meta, (
				dropbox.files.FolderMetadata,
				dropbox.sharing.SharedFolderMetadata
				)):
				bytes = 0
				isdir = True
			else:
				bytes = meta.size
				isdir = False
			
		type_ = (stat.S_IFDIR if isdir else stat.S_IFREG)
		m = calc_mode(type=type_)
		s = make_stat(size=bytes, mode=m)
		return s


class Dropbox_Upload(object):
	"""utility file-like class used for Dropbox-uploads."""
	def __init__(self, client, path, mode):
		self.client = client
		self.path = path
		self.mode = mode
		self.session = None
		self.cursor = None
		self.closed = False

	def write(self, data):
		"""writes some data to the file."""
		if self.closed:
			raise ValueError("I/O operation on closed file")
		if self.session is None:
			# first call
			self.session = self.client.files_upload_session_start(
				data, close=False,
				)
			self.cursor = dropbox.files.UploadSessionCursor(
				self.session.session_id, offset=0
				)
		else:
			self.client.files_upload_session_append_v2(
				data, self.cursor, close=False
				)
		self.cursor.offset += len(data)

	def close(self):
		"""closes the file"""
		if self.closed:
			return
		if self.session is None:
			self.client.files_upload("", self.path, mute=True)
		else:
			commit = dropbox.files.CommitInfo(self.path, mode=OVERWRITE)
			self.client.files_upload_session_finish(
				"", self.cursor, commit
				)
			self.session = None
		self.closed = True
	
	def __del__(self):
		"""called on deletion"""
		self.close()
	
	def __enter__(self):
		"""called when entering a 'with'-context."""
		return self
	
	def __exit__(self, exc_type, exc_value, traceback):
		"""called when exiting a 'with'-context."""
		self.close()
	
	def flush(self):
		"""no-op"""
		pass
	
	def truncate(self, size=-1):
		"""no-op"""
		pass


class Dropbox_Download(object):
	"""
	utility file-like class used for Dropbox-downloads.
	There are two reasons to use this class:
		1. requests.Response.raw does not support seek() and tell()
		2. the 'ls' command checks for filetypes. Due to this, each
			file in a directory is opened. This class improved performance
			by only downloading as much as required into a temporary file.
	"""
	def __init__(self, client, path, mode, buffering, response):
		self.client = client
		self.path = path
		self.mode = mode
		self.buffering = buffering
		self.name = path
		self._response = response
		self._raw = response.raw
		self.closed = False
		self._read = 0
		if "U" in mode:
			tfmode = "w+bU"
		else:
			tfmode = "w+b"
		self._tf = tempfile.TemporaryFile(mode=tfmode)
		self.newlines = None
	
	def close(self):
		"""closes the file"""
		if self.closed:
			return
		self.closed = True
		self._tf.close()
		self._raw.close()
		p = self._tf.name
		if os.path.exists(p):
			os.remove(p)
	
	def __enter__(self):
		"""called when entering a 'with'-context"""
		return self
	
	def __exit__(self, exc_type, exc_value, traceback):
		"""called when exiting a 'with'-context."""
		self.close()
	
	def __del__(self):
		"""called when the object will be deleted"""
		self.close()
	
	def read(self, size=-1):
		"""read at most size bytes from the file"""
		if self.closed:
			raise ValueError("I/O operation on closed file")
		if ((size + self._tf.tell()) > self._read) or (size < 0):
			ccp = self._tf.tell()
			if size >= 0:
				tr = size - (self._read - ccp)
				content = self._raw.read(tr)
			else:
				content = self._raw.read()
			self._read += len(content)
			self._tf.seek(0, os.SEEK_END)
			self._tf.write(content)
			self._tf.seek(ccp, os.SEEK_SET)
		return self._tf.read(size)
	
	def tell(self):
		"""tells the cursor position"""
		return self._tf.tell()
	
	def seek(self, offset, whence=os.SEEK_SET):
		"""sets the cursor position"""
		ccp = self._tf.tell()
		if whence == os.SEEK_SET:
			ncp = offset
		elif whence == os.SEEK_CUR:
			ncp = ccp + offset
		elif whence == os.SEEK_END:
			size = int(self._response.headers["Content-Length"])
			ncp = size + offset
		else:
			raise ValueError("Invalid Value")
		if ncp > self._read:
			toread = ncp - ccp
			self.read(toread)
			self.seek(ccp, os.SEEK_SET) 
			# we need to seek twice to support relative search
		self._tf.seek(offset, whence)
	
	def readline(self, size=-1):
		"""Read one entire line from the file."""
		if "U" in self.mode:
			ends = ("\n", "\r", "\r\n")
		else:
			ends = ("\n", )
		buff = ""
		while True:
			d = self.read(1)
			buff += d
			if any([e in buff for e in ends]):
				return buff
			if (size <= len(buff)) or (not d):
				return buff
	
	def readlines(self, sizehint=None):
		"""
		Read until EOF using readline() and return a list containing the
		lines thus read.
		"""
		# sizehint ignored; see the documentation of file.readlines
		lines = []
		while True:
			line = self.readline()
			if not line:
				break
			lines.append(line)
		return lines
	
	def xreadlines(self):
		"""This method returns the same thing as iter(f)."""
		return self
		
	def __iter__(self):
		if self.closed:
			raise ValueError("I/O operation on closed file")
		return self
	
	def next(self):
		"""returns the next line"""
		line = self.readline()
		if line:
			return line
		else:
			raise StopIteration()
	
	def flush(self):
		"""no-op"""
		pass
	
	def truncate(self, size=-1):
		"""no-op"""
		pass
