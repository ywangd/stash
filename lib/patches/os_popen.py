import os

_stash = globals()["_stash"]


class _PipeEndpoint(object):
	"""this class represents a pipe endpoint."""
	def __init__(self, root, pipe):
		self.__root = root
		self.__pipe = pipe
	
	def __getattr__(self, name):
		"""return attribute name of the pipe."""
		return getattr(self.__pipe, name)
	
	def __hasattr__(self, name):
		"""checks wether the pioe has a attribute called name."""
		return hasattr(self.__pipe, name)
	
	def __repr__(self):
		"""returns the representation of the pipe."""
		return repr(self.__pipe)
	
	def __del__(self):
		"""called on deletion."""
		self.close()
	
	def close(self):
		"""closes the pipe."""
		try:
			os.close(self.__pipe.fileno())
		except OSError:
			pass
		ec = self.__root.get_exit_code(wait=True)
		if ec == 0:
			return None  # see os.popen
		else:
			return ec

		
class _PopenCmd(object):
	"""This class handles the command processing."""
	def __init__(self, cmd, mode, bufsize, shared_eo=False):
		self.cmd = cmd
		self.mode = mode
		self.bufsize = bufsize
		self.fds = []
		self.exitstatus = None
		self.worker = None
		self.shared_eo = shared_eo
		self.chinr, self.chinw = self.create_pipe(wbuf=bufsize)
		self.choutr, self.choutw = self.create_pipe(rbuf=bufsize)
		self.killer = 0
		if shared_eo:
			self.cherrr, self.cherrw = self.choutr, self.choutw
		else:
			self.cherrr, self.cherrw = self.create_pipe(rbuf=bufsize)
	
	def get_pipes(self):
		"""returns the pipes."""
		if not self.shared_eo:
			return (
				_PipeEndpoint(self, self.chinw),
				_PipeEndpoint(self, self.choutr),
				_PipeEndpoint(self, self.cherrr)
				)
		else:
			return (
				_PipeEndpoint(self, self.chinw),
				_PipeEndpoint(self, self.choutr)
				)
	
	def close_fds(self):
		"""close all fds."""
		for fd in self.fds:
			try:
				os.close(fd)
			except os.OSError:
				pass
	
	def create_pipe(self, rbuf=0, wbuf=0):
		"""creates a pipe. returns (readpipe, writepipe)"""
		rfd, wfd = os.pipe()
		self.fds += [rfd, wfd]
		rf, wf = os.fdopen(rfd, "rb", rbuf), os.fdopen(wfd, "wb", wbuf)
		return rf, wf
	
	def run(self):
		"""runs the command."""
		self.worker = _stash(
			input_=self.cmd,
			persistent_level=2,
			is_background=False,
			wait=False,
			add_to_history=None,
			final_ins=self.chinr,
			final_outs=self.choutw,
			final_errs=self.cherrw
			)
	
	def get_exit_code(self, wait=True):
		"""returns the exitcode. 
		If wait is False and the worker has not finishef yet, return None."""
		if self.worker is not None:
			if wait:
				self.worker.join()
			elif self.worker.status() != self.worker.STOPPED:
				return None
			es = self.worker.state.return_value
			return (es * 256) + self.killer
		raise RuntimeError("get_exit_code() called before run()!")
	

def popen(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd.get_pipes()
	cmd.run()
	if mode == "r":
		return pipes[1]
	elif mode == "w":
		return pipes[0]


def popen2(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd.get_pipes()
	cmd.run()
	return pipes[0], pipes[1]


def popen3(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout, child_stderr)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd.get_pipes()
	cmd.run()
	return pipes[0], pipes[1], pipes[2]


def popen4(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout_and_stderr)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=True)
	pipes = cmd.get_pipes()
	cmd.run()
	return pipes[0], pipes[1]


if __name__ == "__main__":
	# testcode
	import select
	cmd = raw_input("cmd: ")
	i, o = popen4(cmd)
	rs = [o]
	ws = [i]
	while True:
		if len(rs + ws) == 0:
			break
		ra, wa, x = select.select(rs, ws, rs + ws)
		for p in x:
			print _stash.text_color("Error in pipe: "+repr(p), "yellow")
			p.close()
			if p in rs:
				rs.remove(p)
			if p in ws:
				ws.remove(p)
			continue
		for p in ra:
			data = p.read(4096)
			if data:
				print data
			else:
				print _stash.text_color("stdout closed", "yellow")
				p.close()
				rs.remove(p)
				ws = []
		#for p in wa:
		#	inp = raw_input()
		#	p.write(inp)
	print _stash.text_color("es:", "yellow"), o.close()
