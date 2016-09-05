"""Interface to FTP-servers."""
import ftplib
import tempfile
import os

from stashutils.core import get_stash

from stashutils.fsi.base import BaseFSI
from stashutils.fsi.errors import OperationFailure, IsDir, IsFile
from stashutils.fsi.errors import AlreadyExists

_stash = get_stash()


class FTPFSI(BaseFSI):
	"""a FSI for FTP-server.
Unfortunally, FTP was designed as a human-readable protocol.
Due to this, the protocol is not completly unified.
This means, that this FSI lad not work on all FTP-servers."""
	def __init__(self, logger=None):
		self.logger = logger
		self.path = "/"
		self.ftp = None
		self.host = None

	def connect(self, *args):
		if self.ftp is not None:
			return "Interface already connected"
		if len(args) < 1 or len(args) > 5:
			return "Invalid argument count"
		user, pswd = None, None
		debug = 0
		# TODO: make the following code less ugly
		if len(args) == 1:
			host = args[0]
			port = 21
			secure = False
		elif len(args) == 2:
			host, port = args
			secure = False
		elif len(args) == 5 or len(args) == 4:
			user = args[2]
			pswd = args[3]
			secure = False
			host = args[0]
			port = args[1]
		if len(args) not in (3, 5):
			# this prevents the elifs from beeing execeuted
			pass
		elif args[-1] == "-s":
			host, port = args[:2]
			secure = True
		elif args[-1] == "-n":
			host, port = args[:2]
			secure = False
		elif args[-1] == "-d":
			host, port = args[:2]
			secure = True
			debug = 2
		else:
			return "Unknown argument(s)"
		self.host = host
		self.port = port
		self.user = user
		try:
			port = int(port)
		except:
			return "Invalid port-argument"
		if secure:
			self.ftp = ftplib.FTP_TLS()
		else:
			self.ftp = ftplib.FTP()
		self.ftp.set_debuglevel(debug)
		try:
			self.ftp.connect(host, port)
		except Exception as e:
			self.close()
			if isinstance(e, EOFError):
				return "EOF"
			return e.message
		else:
			if secure:
				self.log(_stash.text_color("Done", "green"))
				self.log(".\nSecuring Connection... ")
				try:
					self.ftp.prot_p()
				except Exception as e:
					self.close()
					return e.message
			self.log(_stash.text_color("Done", "green"))
			self.log(".\nLogging in... ")
			try:
				self.ftp.login(user, pswd)
			except Exception as e:
				self.close()
				return e.message
			else:
				self.path = self.ftp.pwd()
				return True

	def close(self):
		if self.ftp is not None:
			try:
				self.ftp.quit()
			except:
				try:
					self.ftp.close()
				except:
					pass

	def repr(self):
		raw = "FTP-Session for {u} on {h}:{p}"
		fo = raw.format(u=self.user, h=self.host, p=self.port)
		return fo

	def cd(self, name):
		ap = os.path.join(self.path, name)
		try:
			self.ftp.cwd(ap)
		except Exception as e:
			raise OperationFailure(str(e))
		else:
			self.path = ap

	def mkdir(self, name):
		ap = os.path.join(self.path, name)
		try:
			self.ftp.mkd(ap)
		except Exception as e:
			# test wether the dir exists
			self.get_path()
			try:
				self.cd(ap)
			except Exception:
				raise e
			else:
				raise AlreadyExists("Already exists!")
			raise OperationFailure(str(e))

	def listdir(self):
		try:
			content = self.ftp.nlst(self.path)
			ret = [e.split("/")[-1] for e in content]
			return ret
		except Exception as e:
			raise OperationFailure(str(e))

	def remove(self, name):
		ap = os.path.join(self.path, name)
		# we dont know wether target is a server or a file, so try both
		try:
			self.ftp.delete(ap)
		except Exception as e:
			try:
				self.ftp.rmd(ap)
			except Exception as e2:
				text = _stash.text_color(
					"Error trying to delete file: {e}!\n".format(e=e.message), "red"
					)
				self.log(text)
				text = _stash.text_color(
					"Error trying to delete dir (after file-deletion failed)!\n", "red"
					)
				self.log(text)
				raise OperationFailure(e2.message)

	def open(self, name, mode="rb"):
		ap = os.path.join(self.path, name)
		if mode in ("r", "rb"):
			try:
				tf = tempfile.TemporaryFile()
				self.ftp.retrbinary("RETR " + ap, tf.write, 4096)
				tf.seek(0)
			except Exception as e:
				raise OperationFailure(e.message)
			return tf
		elif "w" in mode:
			return FTP_Upload(self.ftp, ap, mode)

	def get_path(self):
		return self.ftp.pwd()

	def isdir(self, name):
		ap = os.path.join(self.path, name)
		op = self.get_path()
		try:
			self.ftp.cwd(ap)
			return True
		except:
			return False
		finally:
			self.ftp.cwd(op)


class FTP_Upload(object):
	"""utility class used for FTP-uploads.
this class creates a tempfile, which is uploaded to the server when closed."""
	def __init__(self, ftp, path, mode):
		self.ftp = ftp
		self.path = path
		self.mode = mode
		self.tf = tempfile.TemporaryFile()

	def write(self, data):
		self.tf.write(data)

	def close(self):
		self.tf.seek(0)
		try:
			self.ftp.storbinary("STOR "+self.path, self.tf, 4096)
		except Exception as e:
			raise OperationFailure(e.message)
		finally:
			self.tf.close()