"""The FSI for zipfiles"""
import zipfile
import os
import tempfile
import time
import shutil
import datetime
import stat

from io import BytesIO

from stashutils.fsi import base
from stashutils.fsi import errors


# TODO: check filename bug when writing


class ZipfileFSI(base.BaseFSI):
	"""FSI for zipfiles"""
	def __init__(self, logger):
		base.BaseFSI.__init__(self, logger)
		self.logger = logger
		self.path = "/"
		self.zf = None
		self.is_new = True
		self.dirs = ["/"]  # list of dirs with no files in them
		self.log("Warning: The ZipfileFSI has some unfixed bugs!\n")
		# ^^^ These bugs are beyond my abilities (and they seem to be case
		# dependent)
	
	def abspath(self, path):
		"""returns the absolute path for path."""
		p = os.path.join(self.path, path)
		while p.startswith("/"):
			p = p[1:]
		return p
	
	def _getdirs(self):
		"""returns a list of all dirs"""
		dirs = ["/"] + self.dirs
		for name in self.zf.namelist():
			dirpath = os.path.dirname(name)
			if dirpath not in dirs:
				dirs.append(dirpath)
		return dirs
	
	def _update(self, remove=[]):
		"""create a new zipfile with some changes"""
		nzfp = os.path.join(
			tempfile.gettempdir(), "tempzip_{t}.zip".format(t=time.time())
			)
		op = self.zf.fp.name
		pswd = self.zf.pwd
		comment = self.zf.comment
		nzf = zipfile.ZipFile(nzfp, "w", self.zf.compression, True)
		infos = self.zf.infolist()
		for zipinfo in infos:
			add = True
			for rm in remove:
				if zipinfo.filename.startswith(rm):
					add = False
					break
			if not add:
				continue
			ofo = self.zf.open(zipinfo)
			nzf.writestr(zipinfo, ofo.read())
		self.zf.close()
		os.remove(op)
		nzf.close()
		shutil.copy(nzfp, op)
		self.zf = zipfile.ZipFile(op, "a", zipfile.ZIP_DEFLATED, True)
		self.zf.setpassword(pswd)
		self.zf.comment = comment
	
	def connect(self, *args):
		"""open the zipfile"""
		if len(args) != 1:
			return "expected one or two arguments!"
		ap = os.path.abspath(args[0])
		if os.path.exists(ap):
			if not zipfile.is_zipfile(ap):
				return "not a zipfile"
			try:
				self.zf = zipfile.ZipFile(
					ap, "a", zipfile.ZIP_DEFLATED, True
					)
				self.is_new = False
			except Exception as e:
				return e.message
			if len(args) == 2:
				self.zf.setpassword(args[1])
			return True
		else:
			try:
				self.zf = zipfile.ZipFile(
					ap, "w", zipfile.ZIP_DEFLATED, True
					)
				self.is_new = True
			except Exception as e:
				return e.message
			return True
	
	def repr(self):
		"""returns a string representing this fsi"""
		template = "{inz} Zipfile at '{p}'"
		inz = "New" if self.is_new else "Open"
		return template.format(inz=inz, p=self.zf.fp.name)
	
	def listdir(self, path="."):
		ap = self.abspath(path)
		dirlist = self._getdirs()
		namelist = self.zf.namelist()
		names = dirlist + namelist
		content = []
		for name in names:
			dirname = os.path.dirname(name)
			if dirname == ap:
				content.append(name.replace(dirname, ""))
		return content
	
	def cd(self, path):
		np = self.abspath(path)
		dirs = self._getdirs()
		if np not in dirs:
			raise errors.OperationFailure("Dir does not exists!")
		self.path = np
	
	def get_path(self):
		return self.path
	
	def remove(self, path):
		ap = self.abspath(path)
		self._update(remove=[ap])
	
	def mkdir(self, name):
		ap = self.abspath(name)
		self.dirs.append(ap)
	
	def close(self):
		self.zf.close()
	
	def isdir(self, name):
		ap = self.abspath(name)
		return ((ap in self._getdirs()) and not self.isfile(name))
	
	def isfile(self, name):
		ap = self.abspath(name)
		return (ap in self.zf.namelist())
	
	def stat(self, name):
		ap = self.abspath(name)
		self.log("stat: {ap}\n".format(ap=ap))
		isdir = self.isdir(name)
		isfile = self.isfile(name)
		if not (isdir or isfile):
			self.log("stat-target not found.\n")
			raise errors.OperationFailure("Not found!")
		if isdir:
			size = 1
			mtime = None
		else:
			zipinfo = self.zf.getinfo(ap)
			size = zipinfo.file_size
			timestamp = zipinfo.date_time
			dt = datetime.datetime(*timestamp)
			mtime = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
		type_ = (stat.S_IFREG if isfile else stat.S_IFDIR)
		mode = base.calc_mode(type=type_)
		self.log("stat return\n")
		return base.make_stat(
			size=size, mtime=mtime, ctime=mtime, mode=mode
			)
	
	def open(self, name, mode="r", buffering=0):
		ap = self.abspath(name)
		self.log("open {ap} with mode {m}\n".format(ap=ap, m=mode))
		if "r" in mode:
			try:
				reader = ZipReader(self, ap, mode, buffering)
			except:
				raise errors.OperationFailure("Not found!")
			else:
				return reader
		elif "w" in mode:
			if ap in self.zf.namelist():
				self._update(remove=[ap])
			return ZipWriter(self, ap, mode, buffering)
		else:
			raise errors.OperationFailure("Unsupported mode!")
		

class ZipWriter(object):
	"""utility class used for writing to a ZipFile."""
	def __init__(self, root, fp, mode, buffering):
		self.root = root
		self.fp = fp
		self.name = fp
		self.buffering = buffering
		self.mode = mode
		self.sio = BytesIO()
		self.closed = False
	
	def close(self):
		"""called on file close"""
		if self.closed:
			return
		self.closed = True
		content = self.sio.getvalue()
		self.sio.close()
		self.root.zf.writestr(self.fp, content)
	
	def __getattr__(self, name):
		return getattr(self.sio, name)
	
	def __enter__(self):
		return self
	
	def __exit__(self, exc_type, exc_value, exc_tb):
		self.close()
	
	def __del__(self):
		self.close()


class ZipReader(ZipWriter):
	"""utility class for reading a file from a zip."""
	def __init__(self, root, fp, mode, buffering):
		self.root = root
		self.fp = fp
		self.name = fp
		self.buffering = buffering
		self.mode = mode
		self.sio = BytesIO(self.root.zf.read(fp))
		self.closed = False
	
	def close(self):
		if self.closed:
			return
		self.closed = True
		self.sio.close()