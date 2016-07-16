"""This module contains the base class for patches."""
import sys
import imp
import os


_stash = None  # set this


class IncompatiblePatch(Exception):
	"""raised when a patch is incompatible."""
	pass


class BasePatch(object):
	"""
	Baseclass for other patches.
	This class also keeps track wether patches are enabled or not.
	Subclasses should call BasePatch.__init__(self) and should
	overwrite do_enable() and do_disable().
	"""
	PY2 = True  # Python 2 compatibility
	PY3 = False  # Python 3 compatibility
	
	def __init__(self):
		self.enabled = False
	
	def enable(self):
		"""enable the patch."""
		if not self.enabled:
			pyv = sys.version_info[0]
			if pyv == 2 and not self.PY2:
				raise IncompatiblePatch("Python 2 not supported!")
			if pyv == 3 and not self.PY3:
				raise IncompatiblePatch("Python 3 not supported!")
			self.do_enable()
	
	def disable(self):
		"""disable the patch."""
		if self.enabled:
			self.do_disable()
	
	def do_enable(self):
		"""this should be overwritten in subclasses and apply the patch."""
		pass
	
	def do_disable(self):
		"""This should be overwritten in subclasses and remove the patch."""
		pass


class FunctionPatch(BasePatch):
	"""
	This is a baseclass for patches replacing functions or classes.
	Subclasses should redefine self.module and self.function.
	'module' should be a string with the name of the module to load.
	'function' should be a string with the name of the function to replace.
	'replacement' should be the replacement.
	"""
	module = None
	function = None
	replacement = None
	
	def __init__(self):
		BasePatch.__init__(self)
		self.old = None
	
	def do_enable(self):
		if (self.function is None) or (self.module is None) or (self.replacement is None):
			raise ValueError("Invalid Patch definition!")
		if self.module not in sys.modules:
			fin, path, description = imp.find_module(self.module)
			try:
				module = imp.load_module(self.module, fin, path, description)
			finally:
				fin.close()
		else:
			module = sys.modules[self.module]
		self.old = getattr(module, self.function)
		setattr(module, self.function, self.replacement)
	
	def do_disable(self):
		module = sys.modules[self.module]
		if self.old is not None:
			setattr(module, self.function, self.old)


class ModulePatch(BasePatch):
	"""
	This is a baseclass for patches replacing/adding modules.
	Subclasses should overwrite self.relpath to point to the module.
	self.relpath is relative to self.BASEPATH .
	"""
	relpath = None
	BASEPATH = os.path.join(os.path.dirname(__file__), "modules")
	
	def __init__(self):
		if self.relpath is None:
			raise ValueError("Invalid Patch definition!")
		self.path = os.path.join(self.BASEPATH, self.relpath)
		
	def do_enable(self):
		sys.path.insert(
			min(1, len(sys.path)),
			self.path
			)
	
	def do_disable(self):
		if self.path in sys.path:
			sys.path.remove(self.path)


class PatchGroup(BasePatch):
	"""
	This is a baseclass for a group of patches.
	Subclasses should overwrite self.patches.
	"""
	patches = []
	
	def enable(self):
		# we need to overwrite enable() because
		# the patches should check wether they are already enabled
		self.do_enable()
	
	def disable(self):
		# see enable
		self.do_enable()
	
	def do_enable(self):
		for p in self.patches:
			p.enable()
	
	def do_disable(self):
		for p in self.patches:
			p.disable()
