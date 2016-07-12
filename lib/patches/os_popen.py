import os

_stash = globals()["_stash"]


class _PipeEndpoint(object):
	"""this class represents a pipe endpoint."""
	def __init__(self, root, pipe):
		self.__root = root
		self.__pipe = pipe
	
	def __getattr__(self, name):
		return getattr(self.__pipe, name)
	
	def __hasattr__(self, name):
		return hasattr(self.__pipe, name)
	
	def __repr__(self):
		return repr(self.__pipe.fileno()) # debug
		return repr(self.__pipe)
	
	def __del__(self):
		"""called on deletion."""
		self.close()
	
	def close(self):
		"""closes the pipe."""
		print "closing: ", self.__pipe.fileno()
		try:
			os.close(self.__pipe.fileno())
		except OSError:
			pass
		ec = self.__root._get_exit_code()
		if ec == 0:
			return None  # see os.popen
		else:
			return ec

		
class _PopenCmd(object):
	"""This class handles the command processing."""
	def __init__(self, cmd, mode, bufsize, shared_eo=False):
		self.__cmd = cmd
		self.__mode = mode
		self.__bufsize = bufsize
		self.__fds = []
		self.__exitstatus = None
		self.__worker = None
		self.__shared_eo = shared_eo
		self.__chinr, self.__chinw = self.__create_pipe(wbuf=bufsize)
		self.__choutr, self.__choutw = self.__create_pipe(rbuf=bufsize)
		self.__killer = 0
		if shared_eo:
			self.__cherrr, self.__cherrw = self.__choutr, self.__choutw
		else:
			self.__cherrr, self.__cherrw = self.__create_pipe(rbuf=bufsize)
	
	def _get_pipes(self):
		"""returns the pipes."""
		if not self.__shared_eo:
			return (
				_PipeEndpoint(self, self.__chinw),
				_PipeEndpoint(self, self.__choutr),
				_PipeEndpoint(self, self.__cherrr)
				)
		else:
			return (
				_PipeEndpoint(self, self.__chinw),
				_PipeEndpoint(self, self.__choutr)
				)
	
	def __close_fds(self):
		"""close all fds."""
		for fd in self.__fds:
			try:
				os.close(fd)
			except os.OSError:
				pass
	
	def __create_pipe(self, rbuf=0, wbuf=0):
		"""creates a pipe. returns (readpipe, writepipe)"""
		rfd, wfd = os.pipe()
		self.__fds += [rfd, wfd]
		rf, wf = os.fdopen(rfd, "rb", rbuf), os.fdopen(wfd, "wb", wbuf)
		return rf, wf
	
	def _exec(self):
		"""runs the command."""
		self.__worker = _stash(
			input_=self.__cmd,
			persistent_level=2,
			is_background=False,
			wait=False,
			add_to_history=None,
			final_ins=self.__chinr,
			final_outs=self.__choutw,
			final_errs=self.__cherrw
			)
	
	def _get_exit_code(self):
		if self.__worker is not None:
			self.__worker.join()
			es = self.__worker.state.return_value
			return (es * self.__killer) + es
		return 0
	

def popen(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd._get_pipes()
	cmd._exec()
	if mode == "r":
		return pipes[1]
	elif mode == "w":
		return pipes[0]


def popen2(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd._get_pipes()
	cmd._exec()
	return pipes[0], pipes[1]


def popen3(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout, child_stderr)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=False)
	pipes = cmd._get_pipes()
	cmd._exec()
	return pipes[0], pipes[1], pipes[2]


def popen4(cmd, mode="r", bufsize=0):
	"""Execute cmd as a sub-process and return the file objects (child_stdin, child_stdout_and_stderr)."""
	cmd = _PopenCmd(cmd, mode, bufsize, shared_eo=True)
	pipes = cmd._get_pipes()
	cmd._exec()
	return pipes[0], pipes[1]


if __name__ == "__main__":
	# testcode
	import select
	cmd = raw_input("cmd: ")
	i, o = popen3(cmd)
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
