"""The FSI for dropbox."""
# this module is named 'DropBox' instead of 'dropbox' to avoid a naming conflict.
import os
import tempfile

from dropbox import rest

from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists
from stashutils.fsi.base import BaseFSI
from stashutils.dbutils import get_dropbox_client


class DropboxFSI(BaseFSI):
	"""A FSI for accessing dropbox."""
	def __init__(self, logger):
		self.logger = logger
		self.path = "/"
		self.client = None

	def connect(self, *args):
		"""connects to the dropbox. args[0] is the username."""
		if len(args) != 1:
			return "expected one argument!"
		try:
			self.client = get_dropbox_client(
				args[0], False, None, None
				)
		except Exception as e:
			return e.message
		else:
			if self.client is None:
				return "No Dropbox configured for '{u}'.".format(u=args[0])
			return True

	def get_path(self):
		return self.path

	def repr(self):
		info = self.client.account_info()
		name = info["display_name"]
		return "{name}'s Dropbox [CWD: {p}]".format(name=name, p=self.path)

	def close(self):
		pass

	def cd(self, name):
		if name.startswith("/"):
			path = name
		else:
			path = os.path.join(self.path, name)
		if name == "..":
			self.path = "/".join(self.path.split("/")[:-1])
			if self.path == "":
				self.path = "/"
			return
		self.path = path
		try:
			meta = self.client.metadata(path)
			if not meta["is_dir"]:
				raise IsDir()
		except rest.ErrorResponse:
			raise OperationFailure("Not found!")
		else:
			self.path = path

	def listdir(self):
		try:
			meta = self.client.metadata(self.path)
		except rest.ErrorResponse as e:
			raise OperationFailure(e.error_msg)
		return [el["path"].split("/")[-1] for el in meta["contents"]]

	def mkdir(self, name):
		if name.startswith("/"):
			path = name
		else:
			path = os.path.join(self.path, name)
		try:
			self.client.file_create_folder(path)
		except rest.ErrorResponse as e:
			if e.status == 403:
				raise AlreadyExists("Already exists!")
			raise OperationFailure("Can not create dir!")

	def remove(self, name):
		if name.startswith("/"):
			path = name
		else:
			path = os.path.join(self.path, name)
		try:
			self.client.file_delete(path)
		except rest.ErrorResponse:
			raise OperationFailure("Can not delete target!")

	def isdir(self, name):
		if name.startswith("/"):
			path = name
		else:
			path = os.path.join(self.path, name)
		try:
			meta = self.client.metadata(path)
			return meta["is_dir"]
		except rest.ErrorResponse:
			return False

	def isfile(self, name):
		if name.startswith("/"):
			path = name
		else:
			path = os.path.join(self.path, name)
		try:
			meta = self.client.metadata(path)
			return not meta["is_dir"]
		except rest.ErrorResponse:
			return False

	def open(self, name, mode="rb"):
		ap = os.path.join(self.path, name)
		if mode in ("r", "rb"):
			try:
				tf = tempfile.TemporaryFile()
				conn = self.client.get_file(ap)
				while True:
					data = conn.read(4096)
					if data == "":
						break
					tf.write(data)
				tf.seek(0)
			except Exception as e:
				raise OperationFailure(e.message)
			return tf
		elif "w" in mode:
			return Dropbox_Upload(self.client, ap, mode)


class Dropbox_Upload(object):
	"""utility class used for Dropbox-uploads.
this class creates a tempfile, which is uploaded to the server when closed."""
	def __init__(self, client, path, mode):
		self.client = client
		self.path = path
		self.mode = mode
		self.tf = tempfile.TemporaryFile()

	def write(self, data):
		self.tf.write(data)

	def close(self):
		self.tf.seek(0)
		try:
			self.client.put_file(self.path, self.tf, overwrite=True)
		except Exception as e:
			raise OperationFailure(e.message)
		finally:
			self.tf.close()