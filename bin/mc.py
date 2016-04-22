# coding: utf-8
"""easily work with multiple filesystems (e.g. local and FTP) synchronously"""
#the name refers to midnight-commander, but this will probald never be a true counterpart
import os,shutil,cmd,sys,ftplib,tempfile

try:
	_stash=globals()["_stash"]
except:
	_stash=None

#======================
#Errors

class OperationFailure(IOError):
	"""raise this if a operation (e.g. cd) fails. The FSI is responsible for undoing errors."""
class IsDir(OperationFailure):
	"""raise this if a command only works on a file but a dirname is passed."""
class IsFile(OperationFailure):
	"""raise this if a command only works on a dir but a filename is passed."""

#===================
#FSIs

class BaseFSI(object):
	"""
Baseclass for all FSIs.
Other FSIs should subclass this.
This class currently only serves as a documentation, but this may change.
"""
	def __init__(self,master):
		"""called on __init__"""
		self.master=master
	def connect(self,command):
		"""
called to 'connect' to a filesystem. 
This should be no-op on if no connection nor setup is required.
'command' is a string the user passed to the connect-command.
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
	def cd(self,name):
		"""this should change the cwd to name."""
		raise OperationFailure("NotImplemented")
	def get_path(self):
		"""this should return the current path as a string."""
		return "/"
	def remove(self,name):
		"""this should remove name. name may refer either to a dir or a file."""
		raise OperationFailure("NotImplemented")
	def open(self,name,mode):
		"""
		this should return a file-like object opened in mode mode.
		"""
		raise OperationFailure("NotImplemented")
	def mkdir(self,name):
		"""this should create a dir."""
		raise OperationFailure("NotImplemented")
	def close(self):
		"""this should close the interface. There is a chance that this may not be called."""
		pass
	def isdir(self,name):
		"""this should return True if name is an existing directory and False if not."""
		raise OperationFailure("NotImplemented")
	def isfile(self,name):
		"""this should return wether name is an existing file."""
		#default: not isdir(). problem: no exist check
		return not self.isdir(name)

class LocalFSI(BaseFSI):
	"""A FSI for the local filesystem."""
	def __init__(self,master):
		self.master=master
		self.path=os.getcwd()
	def connect(self,args):
		return True#no setup required; connect is allways successful
	def repr(self):
		return "Local Filesystem [CWD: {p}]".format(p=self.path)
	def listdir(self):
		try:
			return os.listdir(self.path)
		except Exception as e:
			raise OperationFailure(str(e))
	def cd(self,name):
		if name=="..":
			self.path=os.path.dirname(self.path)
			return
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif not os.path.isdir(ap):
			raise IsFile()
		else:
			self.path=ap
	def get_path(self):
		return self.path
	def remove(self,name):
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
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
	def open(self,name,mode):
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
		#if not (os.path.exists(ap)):
		#	raise OperationFailure("Not found")
		if os.path.isdir(ap):
			raise IsDir()
		else:
			try:
				return open(ap,mode)
			except Exception as e:
				raise OperationFailure(str(e))
	def mkdir(self,name):
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
		if os.path.exists(ap):
			raise OperationFailure("Already exists")
		else:
			try:
				os.mkdir(ap)
			except Exception as e:
				raise OperationFailure(str(e))
	def close(self):
		pass
	def isdir(self,name):
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
		return os.path.isdir(ap)
	def isfile(self,name):
		if os.path.isabs(name): ap=name
		else: ap=os.path.join(self.path,name)
		return os.path.isfile(ap)

class FTPFSI(BaseFSI):
	"""a FSI for FTP-server.
Unfortunally, FTP was designed as a human-readable protocol.
Due to this, the protocol is not completly unified.
This means, that this FSI lad not work on all FTP-servers."""
	def __init__(self,master):
		self.master=master
		self.path="/"
		self.ftp=None
		self.host=None
	def connect(self,cmd):
		if self.ftp is not None:
			return "Interface already connected"
		args=cmd.split()
		if len(args)<1 or len(args)>5:
			return "Invalid argument count"
		user,pswd=None,None
		debug=0
		#TODO: make the following code less ugly
		if len(args)==1:
			host=args[0]
			port=21
			secure=False
		elif len(args)==2:
			host,port=args
			secure=False
		elif len(args)==5 or len(args)==4:
			user=args[2]
			pswd=args[3]
			secure=False
			host=args[0]
			port=args[1]
		if len(args) not in (3,5):
			#this prevents the elifs from beeing execeuted
			pass
		elif args[-1]=="-s":
			host,port=args[:2]
			secure=True
		elif args[-1]=="-n":
			host,port=args[:2]
			secure=False
		elif args[-1]=="-d":
			host,port=args[:2]
			secure=True
			debug=2
		else:
			return "Unknown argument(s)"
		self.host=host
		self.port=port
		self.user=user
		try:
			port=int(port)
		except:
			return "Invalid port-argument"
		if secure:
			self.ftp=ftplib.FTP_TLS()
		else:
			self.ftp=ftplib.FTP()
		self.ftp.set_debuglevel(debug)
		try:
			self.ftp.connect(host,port)
		except Exception as e:
			self.close()
			if isinstance(e,EOFError):
				return "EOF"
			return e.message
		else:
			if secure:
				self.master.stdout.write("Done.\nSecuring Connection... ")
				try:
					self.ftp.prot_p()
				except Exception as e:
					self.close()
					return e.message
				self.master.stdo
			self.master.stdout.write("Done.\nLogging in... ")
			try:
				self.ftp.login(user,pswd)
			except Exception as e:
				self.close()
				return e.message
			else:
				self.path=self.ftp.pwd()
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
		return "FTP-Session for {u} on {h}:{p}".format(u=self.user,h=self.host,p=self.port)
	def cd(self,name):
		ap=os.path.join(self.path,name)
		try:
			self.ftp.cwd(ap)
		except Exception as e:
			raise OperationFailure(str(e))
		else:
			self.path=ap
	def mkdir(self,name):
		ap=os.path.join(self.path,name)
		try:
			self.ftp.mkd(ap)
		except Exception as e:
			raise OperationFailure(str(e))
	def listdir(self):
		try:
			content=self.ftp.nlst(self.path)
			ret=[e.split("/")[-1] for e in content]
			return ret
		except Exception as e:
			raise OperationFailure(str(e))
	def remove(self,name):
		ap=os.path.join(self.path,name)
		#we dont know wether target is a server or a file, so try both
		try:
			self.ftp.delete(ap)
		except Exception as e:
			try:
				self.ftp.rmd(ap)
			except Exception as e2:
				self.master.stdout.write("Error trying to delete file: {e}!\n".format(e=e.message))
				self.master.stdout.write("Error trying to delete dir (after file-deletion failed)!\n")
				raise OperationFailure(e2.message)
	def open(self,name,mode="rb"):
		ap=os.path.join(self.path,name)
		if mode in ("r","rb"):
			try:
				tf=tempfile.TemporaryFile()
				self.ftp.retrbinary("RETR "+ap,tf.write,4096)
				tf.seek(0)
			except Exception as e:
				raise OperationFailure(e.message)
			return tf
		elif "w" in mode:
			return FTP_Upload(self.ftp,ap,mode)
	def get_path(self):
		return self.ftp.pwd()
	def isdir(self,name):
		ap=os.path.join(self.path,name)
		op=self.get_path()
		try:
			self.ftp.cwd(ap)
			return True
		except:
			return False
		finally:
			self.ftp.cwd(op)

#=============================
#utility classes and functions

class FTP_Upload(object):
	"""utility class used for FTP-uploads.
this class creates a tempfile, which is uploded onto the server when closed."""
	def __init__(self,ftp,path,mode):
		self.ftp=ftp
		self.path=path
		self.mode=mode
		self.tf=tempfile.TemporaryFile()
	def write(self,data):
		self.tf.write(data)
	def close(self):
		self.tf.seek(0)
		try:
			self.ftp.storbinary("STOR "+self.path,self.tf,4096)
		except Exception as e:
			raise OperationFailure(e.message)
		finally:
			self.tf.close()


#=============================
#Register FSIs here

INTERFACES={
"local":LocalFSI,
"ftp":FTPFSI,
}

#=============================
#User-Interface

class McCmd(cmd.Cmd):
	prompt="(mc)"
	intro="Entering mc's command-loop.\nType 'help' for help and 'exit' to exit."
	use_rawinput=True
	def __init__(self):
		cmd.Cmd.__init__(self)
		self.FSIs={}
	def do_connected(self,cmd):
		"""prints a list of connected interfaces and their id."""
		if len(self.FSIs.keys())==0:
			self.stdout.write("No Interfaces connected.\n")
		for k in sorted(self.FSIs.keys()):
			i=self.FSIs[k]
			name=i.repr()
			self.stdout.write("{k}: {n}\n".format(k=k,n=name))
	def do_exit(self,cmd=""):
		"""exit: quits the script."""
		self.stdout.write("closing interfaces... ")
		for k in self.FSIs.keys():
			try: self.FSIs[k].close()
			except: pass
			del self.FSIs[k]
		self.stdout.write("Done.\ngoodbye!\n")
		sys.exit(0)
	do_EOF=do_quit=do_exit
	def do_connect(self,cmd):
		"""connect <id> <type> [args]: opens a new interface."""
		args=cmd.split()
		if len(args)<2:
			self.stdout.write("Error: expected at least 2 arguments!\n")
			return
		ID,name=args[0],args[1]
		if len(args)>2:
			args=" ".join(args[2:])
		else:
			args=""
		try:
			ID=int(ID)
		except ValueError:
			self.stdout.write("Error: expected a integer!\n")
			return
		if ID in self.FSIs:
			self.stdout.write("Error: ID already registered!\n")
			return
		if name not in INTERFACES:
			self.stdout.write("Error: FSI not found!\n")
			return
		self.stdout.write("Creating Interface... ")
		fsic=INTERFACES[name]
		fsi=fsic(self)
		self.stdout.write("Done.\nConnecting... ")
		try:
			state=fsi.connect(args)
		except OperationFailure as e:
			self.stdout.write("Error: {e}!\n".format(e=e.message))
			return
		if state is True:
			self.FSIs[ID]=fsi
			self.stdout.write("Done.\n")
		elif isinstance(state,str):
			self.stdout.write("Error: {e}!\n".format(e=state))
		else:
			self.stdout.write("Error: cannot interpret return-Value of connect()!\n")
			return
	def do_disconnect(self,command):
		"""disconnect <interface>: close 'interface'."""
		try:
			ID=int(command)
		except:
			self.stdout.write("Error: expected a int as argument!\n")
			return
		if ID not in self.FSIs:
			self.stdout.write("Error: ID does not refer to any Interface!\n")
			return
		try:
			self.FSIs[ID].close()
		except OperationFailure as e:
			self.stdout.write("Error closing Interface: {m}!\n".format(m=e.message))
		del self.FSIs[ID]
		self.stdout.write("Interface closed.\n")
	def do_shell(self,command):
		"""shell <command>: run 'command' in shell"""
		if _stash is not None:
			_stash(command)
		else:
			p=os.popen(command)
			content=p.read()
			code=p.close()
			self.stdout.write(content+"\n")
			self.stdout.write("Exit status: {s}\n".format(s=code))
	def do_cd(self,command):
		"""cd <interface> <dirname>: change path of 'interface' to 'dirname'."""
		fsi,name=self.parse_fs_command(command,nargs=1)
		if (fsi is None) or (name is None):
			return
		try:
			isdir=fsi.isdir(name)
		except:
			isdir=True#lets just try. It worked before isdir() was added so it should still work
		if not isdir:
			self.stdout.write("Error: dirname does not refer to a dir!\n")
			return
		try:
			fsi.cd(name)
		except IsFile:
			self.stdout.write("Error: dirname does not refer to a dir!\n")
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
	def do_path(self,command):
		"""path <interface>: shows current path of 'interface'."""
		fsi,name=self.parse_fs_command(command,nargs=0)
		if (fsi is None) or (name is None):
			return
		try:
			self.stdout.write(fsi.get_path()+"\n")
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
	do_cwd=do_pwd=do_path
	def do_ls(self,command):
		"""ls <interface>: shows the content of the current dir of 'interface'."""
		fsi,name=self.parse_fs_command(command,nargs=0)
		if (fsi is None) or (name is None):
			return
		try:
			content=fsi.listdir()
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
		else:
			self.stdout.write("  "+"\n  ".join(content)+"\n")
	do_dir=do_ls
	def do_rm(self,command):
		"""rm <interface> <name>: removes file/dir 'name'."""
		fsi,name=self.parse_fs_command(command,nargs=1)
		if (fsi is None) or (name is None):
			return
		self.stdout.write("Removing... ")
		try:
			fsi.remove(name)
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
		else:
			self.stdout.write("Done.\n")
	do_del=do_rm
	def do_mkdir(self,command):
		"""mkdir <interface> <name>: creates the dir 'name'."""
		fsi,name=self.parse_fs_command(command,nargs=1)
		if (fsi is None) or (name is None):
			return
		self.stdout.write("Creating dir... ")
		try:
			fsi.mkdir(name)
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
		else:
			self.stdout.write("Done.\n")
	def do_cp(self,command):
		"""cp <ri> <rf> <wi> <wn>: copy file 'rf' from 'ri' to file 'wf' on 'wi'."""
		args=command.split()
		if len(args)!=4:
			self.stdout.write("Error: invalid argument count!\n")
			return
		rfi,rfp,wfi,wfp=args
		try:
			rfi,wfi=int(rfi),int(wfi)
		except ValueError:
			self.stdout.write("Error: Expected integers for first and third argument!\n")
			return
		if (rfi not in self.FSIs) or (wfi not in self.FSIs):
			self.stdout.write("Error: Interface not found!\n")
			return
		rfsi=self.FSIs[rfi]
		wfsi=self.FSIs[wfi]
		isfile=rfsi.isfile(rfp)
		isdir=rfsi.isdir(rfp)
		if isfile:
			try:
				self.stdout.write("Opening infile... ")
				rf=rfsi.open(rfp,"rb")
				self.stdout.write("Done.\nOpening outfile... ")
				wf=wfsi.open(wfp,"wb")
				self.stdout.write("Done.\nCopying... ")
				while True:
					data=rf.read(4096)
					if len(data)==0:
						break
					wf.write(data)
				self.stdout.write("Done.\n")
			except IsDir:
				self.stdout.write("Error: expected a filepath!\n")
				return
			except OperationFailure as e:
				self.stdout.write("Error: {m}!\n".format(m=e.message))
				return
			finally:
				self.stdout.write("Closing infile... ")
				try:
					rf.close()
					self.stdout.write("Done.\n")
				except Exception as e:
					self.stdout.write("Error: {m}!\n".format(m=e.message))
				self.stdout.write("Closing outfile... ")
				try:
					wf.close()
					self.stdout.write("Done.\n")
				except Exception as e:
					self.stdout.write("Error: {m}!\n".format(m=e.message))
		elif isdir:
			crp=rfsi.get_path()
			cwp=wfsi.get_path()
			rfsi.cd(rfp)
			if not wfp in wfsi.listdir():
				self.stdout.write("Creating dir '{n}'... ".format(n=wfp))
				wfsi.mkdir(wfp)
				self.stdout.write("Done.\n")
			wfsi.cd(wfp)
			try:
				content=rfsi.listdir()
				for fn in content:
					subcommand="cp {rfi} {name} {wfi} {name}".format(rfi=rfi,name=fn,wfi=wfi)
					self.onecmd(subcommand)
			except OperationFailure as e:
				self.stdout.write("Error: {e}!\n".format(e=e.message))
				return
			finally:
				rfsi.cd(crp)
				wfsi.cd(cwp)
		else:
			self.stdout.write("Error: Not found!\n")
			return
	do_copy=do_cp
	def do_mv(self,command):
		"""mv <ri> <rf> <wi> <wn>: move file 'rf' from 'ri' to file 'wf' on 'wi'."""
		args=command.split()
		if len(args)!=4:
			self.stdout.write("Error: invalid argument count!\n")
			return
		rfi,rfp,wfi,wfp=args
		try:
			rfi,wfi=int(rfi),int(wfi)
		except ValueError:
			self.stdout.write("Error: Expected integers for first and third argument!\n")
			return
		if (rfi not in self.FSIs) or (wfi not in self.FSIs):
			self.stdout.write("Error: Interface not found!\n")
			return
		rfsi=self.FSIs[rfi]
		wfsi=self.FSIs[wfi]
		isdir=rfsi.isdir(rfp)
		isfile=rfsi.isfile(rfp)
		if isfile:
			try:
				self.stdout.write("Opening file to read... ")
				rf=rfsi.open(rfp,"rb")
				self.stdout.write("Done.\nOpening file to write... ")
				wf=wfsi.open(wfp,"wb")
				self.stdout.write("Done.\nCopying... ")
				while True:
					data=rf.read(4096)
					if len(data)==0:
						break
					wf.write(data)
				self.stdout.write("Done.\n")
			except IsDir:
				self.stdout.write("Error: expected a filepath!\n")
				return
			except OperationFailure as e:
				self.stdout.write("Error: {m}!\n".format(m=e.message))
				return
			finally:
				self.stdout.write("Closing infile... ")
				try:
					rf.close()
					self.stdout.write("Done.\n")
				except Exception as e:
					self.stdout.write("Error: {m}!\n".format(m=e.message))
				self.stdout.write("Closing outfile... ")
				try:
					wf.close()
					self.stdout.write("Done.\n")
				except Exception as e:
					self.stdout.write("Error: {m}!\n".format(m=e.message))
					return
				self.stdout.write("Deleting Original... ")
				try: rfsi.remove(rfp)
				except OperationFailure as e:
					self.stdout.write("Error: {m}!\n".format(m=e.message))
				else:
					self.stdout.write("Done.\n")
		elif isdir:
			crp=rfsi.get_path()
			cwp=wfsi.get_path()
			rfsi.cd(rfp)
			if not wfp in wfsi.listdir():
				self.stdout.write("Creating dir '{n}'... ".format(n=wfp))
				wfsi.mkdir(wfp)
				self.stdout.write("Done.\n")
			wfsi.cd(wfp)
			try:
				content=rfsi.listdir()
				for fn in content:
					subcommand="mv {rfi} {name} {wfi} {name}".format(rfi=rfi,name=fn,wfi=wfi)
					self.onecmd(subcommand)
				rfsi.cd(crp)
				rfsi.remove(rfp)
			except OperationFailure as e:
				self.stdout.write("Error: {e}!\n".format(e=e.message))
				return
			finally:
				rfsi.cd(crp)
				wfsi.cd(cwp)
		else:
			self.stdout.write("Error: Not found!\n")
			return
	do_move=do_mv
	def do_cat(self,command):
		"""cat <interface> <file> [--binary]: shows the content of target file on 'interface'.
if --binary is specified, print all bytes directly.
otherwise, print repr(content)[1:-1]
"""
		fsi,args=self.parse_fs_command(command,nargs=-1,ret=tuple)
		if (fsi is None) or (args is None):
			return
		if len(args)==2:
			if args[1] in ("-b","--binary"):#never print nullbytes until explictly told.
				binary=True
			else:
				self.stdout.write("Error: Unknown read-mode!\n")
				return
			name,binary=args[0],binary
		elif len(args) not in (1,2):
			self.stdout.write("Error: invalid argument count!\n")
			return
		else:
			name,binary=args[0],False
		self.stdout.write("Reading file... ")
		try:
			f=fsi.open(name,"r"+("b" if binary else ""))
			content=f.read()
		except IsDir:
			self.stdout.write("Error: expected a filepath!\n")
		except OperationFailure as e:
			self.stdout.write("Error: {m}\n".format(m=e.message))
		else:
			self.stdout.write("Done.\n")
			if not binary:
				content=repr(content)[1:-1]
			self.stdout.write("\n{c}\n".format(c=content))
		finally:
			try: f.close()
			except: pass
	def parse_fs_command(self,command,nargs=0,ret=str):
		"""parses a filesystem command. returns the interface and the actual command.
nargs specifies the number of arguments, -1 means any number."""
		args=command.split()
		if len(args)<1 or (len(args)!=nargs+1 and nargs!=-1):
			self.stdout.write("Error: invalid argument count!\n")
			return None,None
		try: i=int(args[0])
		except ValueError:
			self.stdout.write("Error: expected an integer as first argument!\n")
			return None,None
		if i not in self.FSIs:
			self.stdout.write("Error: Interface not found!\n")
			return None,None
		if ret==str:
			if len(args)>1:
				args=" ".join(args[1:])
			else:
				args=""
		elif ret==tuple:
			args=args[1:]
		else:
			raise ValueError("Unknown return type!")
		fsi=self.FSIs[i]
		return fsi,args
	def help_usage(self,*args):
		"""prints help about the usage."""
		help="""USAGE
===============
This guide describes how to use mc.

1.) using filesystem
	First, you need to connect to a filesystem.
	Use the 'connect'-command for this.
	Usage:
		connect <id> <fsi-name> [args [args ...]]
		
		'id' is a number used to identify the connection in commands.
		'fsi-name' is the name of the FSI you want to use (e.g. 'local').
		'args' is passed to the FSI and may contain server, username...
	Example:
		connect 1 local
			>opens the local filesystem.
			>you can later use this filesystem by passing 1 to commands.
		connect 2 ftp ftp.example.org 21 YourName YourPswd -s
			>connects to FTP-server ftp.example.org on port 21
			>switch over to SFTP
			>login as YourName with YourPswd
			>you can later use this filesystem by passing 2 to commands.
	If you want to get a list of connected filesystems, use 'connected'.
	If you want to disconnect, use disconnect <id>.
	If you want to get a list of aviable FSIs, use help fsis.
	If you want to see help on a FSI, use help fsi_<name>
2.) Using commands
	After you are connected, you can use any aviable command.
	To get a list of aviable commands, type '?' or 'help'.
	To see the Usage of a command, use 'help <command>'.
3.) Quitting
	To quit, use the 'exit' command.
4.) Tips
	You can run shell commands while using mc:
		!echo test
		shell python
"""
		self.stdout.write(help+"\n")
	def help_fsis(self,*args):
		"""shows a list of aviable FSIs"""
		av="""Aviable FSIs:
local: the local filesystem
ftp: a FTP-client
"""
		self.stdout.write(av+"\n")
	def help_fsi_local(self,*args):
		"""shows a list of aviable FSIs"""
		av="""Help on FSI local:
	The local filesystem.
	USAGE:
		'connect ' does not require any additional arguments.
"""
		self.stdout.write(av+"\n")
	def help_fsi_ftp(self,*args):
		"""shows a list of aviable FSIs"""
		av="""Help on FSI ftp::
	Use a FTP-server as a filesystem.
	WARNING:
		Unless explicitly told, this uses a non-secure connection.
	INFO: 
		FTP is designed as a human-readable protocol.
		Different servers may use different commands and different responses.
		This means that the 'ftp'-FSI may not work with all FTP-servers.
	NOTE:
		The FTP-FSI doesnt work on the server-files.
		Instead, it uses a workaround:
			When reading a FTP-file, the file is instead downloaded into a tempfile and this is read after the download.
			When writing to a FTP-server, instead a tempfile is created and uploaded when it is closed.
			This leads to some 'weird' operation times.
	USAGE:
		connect <ID> ftp <host> [port] [mode or user] [pswd] [mode]
		
		'ID': see 'help connect'
		'host': the IP of the FTP-server
		'port': port of the FTP-server. 21 if not specified.
		'mode or user':
			if len(args)==5:
				the type of the connection. see mode
			else:
				the username to use for login.
				defaults to 'anonymous'
		'pswd': the password to use for login. Defaults to 'anonymous@'
		'mode':
			one of:
				'-s': use a secure connection.
				'-n': dont use a secure connection (default)
				'-d': use a secure connection and set debug to max.
		
"""
		self.stdout.write(av+"\n")

if __name__=="__main__":
	McCmd().cmdloop()
