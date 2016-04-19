# coding: utf-8
"""easily work on two filesystems (e.g. local and FTP)"""
#the name refers to midnight-commander, but this will probald never be a true counterpart
import os,shutil,cmd,sys

try:
	stash=globals()["_stash"]
except:
	stash=None

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
This currently only serves as a documentation, but this mad change.
"""
	def __init__(self):
		"""called on __init__"""
		pass
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
	def getpath(self):
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

class LocalFSI(BaseFSI):
	"""A FSI for the local filesystem."""
	def __init__(self):
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
		ap=os.path.join(self.path,name)
		if not os.path.exists(ap):
			raise OperationFailure("Not found")
		elif not os.path.isdir(ap):
			raise IsFile()
		else:
			self.path=ap
	def get_path(self):
		return self.path
	def remove(self,name):
		ap=os.path.join(self.path,name)
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
		ap=os.path.join(self.path,name)
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
		ap=os.path.join(self.path,name)
		if os.path.exists(ap):
			raise OperationFailure("Already exists")
		else:
			try:
				os.mkdir(ap)
			except Exception as e:
				raise OperationFailure(str(e))
	def close(self):
		pass

#========================
#Register FSIs here

INTERFACES={
"local":LocalFSI,
}

#=========================
#User-Interface

class McCmd(cmd.Cmd):
	prompt="(mc)"
	intro="Entering mc's command-loop.\nType 'help' for help and 'exit' to exit"
	use_rawinput=True
	def __init__(self):
		cmd.Cmd.__init__(self)
		self.FSIs={}
	def do_connected(self,cmd):
		"""prints a list of connected interfaces and their id."""
		if len(self.FSIs.keys())==0:
			self.stdout.write("No Interfaces connected.\n")
		for k in self.FSIs.keys():
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
		fsi=fsic()
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
		if stash is not None:
			stash(command)
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
			try:
				rf.close()
			except:
				pass
			try:
				wf.close()
			except:
				pass
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
			self.stdout.write("Done.\nDeleting Original... ")
			rfsi.remove(rfp)
			self.stdout.write("Done.\n")
		except IsDir:
			self.stdout.write("Error: expected a filepath!\n")
			return
		except OperationFailure as e:
			self.stdout.write("Error: {m}!\n".format(m=e.message))
			return
		finally:
			try:
				rf.close()
			except:
				pass
			try:
				wf.close()
			except:
				pass
	do_move=do_mv
	def do_cat(self,command):
		"""ls <interface> <file> [--binary]: shows the content of target file on 'interface'.
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
		

if __name__=="__main__":
	McCmd().cmdloop()