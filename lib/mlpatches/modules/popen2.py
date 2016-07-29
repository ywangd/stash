"""Subprocesses with accessible I/O streams"""
from mlpatches import os_popen
from mlpatches.l2c import _get_str


def popen2(cmd, bufsize=0, mode="t"):
	"""Executes cmd as a sub-process. Returns the file objects (child_stdout, child_stdin)."""
	command = _get_str(cmd)
	i, o = os_popen.popen2(None, command, mode, bufsize)
	return o, i


def popen3(cmd, bufsize=0, mode="t"):
	"""Executes cmd as a sub-process. Returns the file objects (child_stdout, child_stdin, child_stderr)."""
	command = _get_str(cmd)
	i, o, e= os_popen.popen3(None, command, mode, bufsize)
	return o, i, e


def popen4(cmd, bufsize=0, mode="t"):
	"""Executes cmd as a sub-process. Returns the file objects (child_stdout_and_stderr, child_stdin)."""
	command = _get_str(cmd)
	i, oe = os_popen.popen4(None, command, mode, bufsize)
	return oe, i


class Popen3(object):
	"""This class represents a child process. Normally, Popen3 instances are created using the popen2() and popen3() factory functions described above.

If not using one of the helper functions to create Popen3 objects, the parameter cmd is the shell command to execute in a sub-process. The capturestderr flag, if true, specifies that the object should capture standard error output of the child process. The default is false. If the bufsize parameter is specified, it specifies the size of the I/O buffers to/from the child process."""
	def __init__(self, cmd, capture_stderr=False, bufsize=0):
		strcmd = _get_str(cmd)
		self._p = os_popen._PopenCmd(strcmd, "w", bufsize, shared_eo=False)
		self._p.run()
		self.tochild = self._p.chinw
		self.fromchild = self._p.choutr
		if capture_stderr:
			self.childerr = self._p.cherrr
		else:
			self.childerr = None
		self.pid = self._p.worker.job_id
	
	def poll(self):
		"""Returns -1 if child process has not completed yet, or its status code (see wait()) otherwise."""
		if self._p.worker.is_alive():
			return -1
		else:
			return self._p.worker.state.return_value
	
	def wait(self):
		"""Waits for and returns the status code of the child process. The status code encodes both the return code of the process and information about whether it exited using the exit() system call or died due to a signal. Functions to help interpret the status code are defined in the os module; see section Process Management for the W*() family of functions."""
		self._p.worker.join()
		return self._p.worker.state.return_value


class Popen4(Popen3):
	"""Similar to Popen3, but always captures standard error into the same file object as standard output. These are typically created using popen4()."""
	def __init__(self, cmd, bufsize=1):
		strcmd = _get_str(cmd)
		self._p = os_popen._PopenCmd(strcmd, "w", bufsize, shared_eo=True)
		self._p.run()
		self.tochild = self._p.chinw
		self.fromchild = self._p.choutr
		self.childerr = None
		self.pid = self._p.worker.job_id
