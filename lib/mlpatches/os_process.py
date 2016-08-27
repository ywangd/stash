"""
This module contains patches for the 'os'-module to make StaSh's thread-system like a process-system (from the view of the script)"""
import os
import threading
from mlpatches import base

_stash = base._stash

def getpid(patch):
	"""Return the current process id."""
	ct = threading.current_thread()
	if isinstance(ct, _stash.runtime.ShThread):
		return ct.job_id
	else:
		return -1

def getppid(patch):
	"""Return the parents process id."""
	ct = threading.current_thread()
	if isinstance(ct, _stash.runtime.ShThread):
		pt = ct.parent
	else:
		return -1
	if hasattr(pt, "job_id"):
		return pt.job_id
	else:
		# ShRuntime
		return 0

def kill(patch, pid, sig):
	"""Send signal sig to the process pid. Constants for the specific signals available on the host platform are defined in the signal module"""
	_stash("kill {pid}".format(pid = pid))
