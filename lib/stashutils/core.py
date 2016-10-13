"""core utilities for StaSh-scripts"""
import threading
from stash.system import shthreads


def get_stash():
	"""
	returns the currently active StaSh-instance.
	returns None if it can not be found.
	This is useful for modules.
	"""
	if "_stash" in globals():
		return globals()["_stash"]
	for thr in threading.enumerate():
		if isinstance(thr, shthreads.ShBaseThread):
			ct = thr
			while not ct.is_top_level():
				ct = ct.parent
			return ct.parent.stash
	return None
