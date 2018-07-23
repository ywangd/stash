"""functions and classes related to wheels."""
import os
import shutil
import tempfile
import json
import re
import zipfile

import six
from six.moves import configparser

from stashutils.extensions import create_command


class WheelError(Exception):
	"""Error related to a wheel."""
	pass


def parse_wheel_name(filename):
	"""
	Parse the filename of a wheel and return the information as dict.
	"""
	if not filename.endswith(".whl"):
		raise WheelError("PEP427 violation: wheels need to end with '.whl'")
	else:
		filename = filename[:-4]
	splitted = filename.split("-")
	distribution = splitted[0]
	version = splitted[1]
	if len(splitted) == 6:
		build_tag = splitted[2]
		python_tag = splitted[3]
		abi_tag = splitted[4]
		platform_tag = splitted[5]
	elif len(splitted) == 5:
		build_tag = None
		python_tag = splitted[2]
		abi_tag = splitted[3]
		platform_tag = splitted[4]
	else:
		raise WheelError("PEP427 violation: invalid naming schema")
	return {
		"distribution": distribution,
		"version": version,
		"build_tag": build_tag,
		"python_tag": python_tag,
		"abi_tag": abi_tag,
		"platform_tag": platform_tag,
	}


def escape_filename_component(fragment):
	"""
	Escape a component of the filename as specified in PEP 427.
	"""
	return re.sub("[^\w\d.]+", "_", fragment, re.UNICODE)


def generate_filename(
	distribution,
	version,
	build_tag=None,
	python_tag=None,
	abi_tag=None,
	platform_tag=None,
	):
	"""
	Generate a filename for the wheel and return it.
	"""
	if python_tag is None:
		if six.PY3:
			python_tag = "py3"
		else:
			python_tag = "py2"
	if abi_tag is None:
		abi_tag = "none"
	if platform_tag is None:
		platform_tag = "any"
	return "{d}-{v}{b}-{py}-{a}-{p}.whl".format(
		d=escape_filename_component(distribution),
		v=escape_filename_component(version),
		b=("-" + escape_filename_component(build_tag) if build_tag is not None else ""),
		py=escape_filename_component(python_tag),
		a=escape_filename_component(abi_tag),
		p=escape_filename_component(platform_tag),
		)


def wheel_is_compatible(filename):
	"""
	Return True if the wheel is compatible, False otherwise.
	"""
	data = parse_wheel_name(filename)
	if ("py2.py3" in data["python_tag"]) or ("py3.py2" in data["python_tag"]):
		# only here to skip elif/else
		pass
	elif six.PY3:
		if not data["python_tag"].startswith("py3"):
			return False
	else:
		if not data["python_tag"].startswith("py2"):
			return False
	if data["abi_tag"].lower() != "none":
		return False
	if data["platform_tag"].lower() != "any":
		return False
	return True


class BaseHandler(object):
	"""
	Baseclass for installation handlers.
	"""
	name = "<name not set>"
	
	def __init__(self, wheel, verbose=False):
		self.wheel = wheel
		self.verbose = verbose
	
	def copytree(self, src, dest, remove=False):
		"""copies a directory tree."""
		if self.verbose:
			print("Copying {s} -> {d}".format(s=src, d=dest))
		if os.path.isfile(src):
			if os.path.isdir(dest):
				dest = os.path.join(dest, os.path.basename(src))
			if os.path.exists(dest) and remove:
				os.remove(dest)
			shutil.copy(src, dest)
			return dest
		else:
			target = os.path.join(
				dest,
				os.path.basename(os.path.normpath(src)),
				)
			if os.path.exists(target) and remove:
				shutil.rmtree(target)
			shutil.copytree(src, target)
			return target
	
	@property
	def distinfo_name(self):
		"""the name of the *.dist-info directory."""
		data = parse_wheel_name(self.wheel.filename)
		return "{pkg}-{v}.dist-info".format(
			pkg=data["distribution"],
			v=data["version"],
			)


class TopLevelHandler(BaseHandler):
	"""Handler for 'top_level.txt'"""
	name = "top_level.txt installer"
	
	def handle_install(self, src, dest):
		tltxtp = os.path.join(src, self.distinfo_name, "top_level.txt")
		files_installed = []
		with open(tltxtp, "r") as fin:
			for pkg_name in fin:
				pure = pkg_name.replace("\r", "").replace("\n", "")
				sp = os.path.join(src, pure)
				if os.path.exists(sp):
					p = self.copytree(sp, dest, remove=True)
				elif os.path.exists(sp + ".py"):
					dp = os.path.join(dest, pure + ".py")
					p = self.copytree(sp + ".py", dp, remove=True)
				else:
					raise WheelError("top_level.txt entry '{e}' not found in toplevel directory!".format(e=pure))
				files_installed.append(p)
		return files_installed


class ConsoleScriptsHandler(BaseHandler):
	"""Handler for 'console_scripts'."""
	name = "console_scripts installer"
	
	def handle_install(self, src, dest):
		eptxtp = os.path.join(src, self.distinfo_name, "entry_points.txt")
		if not os.path.exists(eptxtp):
			if self.verbose:
				print("No entry_points.txt found, skipping.")
			return
		parser = configparser.ConfigParser()
		try:
			parser.read(eptxtp)
		except configparser.MissingSectionHeaderError:
			# print message and return
			if self.verbose:
				print("No section headers found in entry_points.txt, passing.")
				return
		if not parser.has_section("console_scripts"):
			if self.verbose:
				print("No console_scripts definition found, skipping.")
			return
		
		files_installed = []
		
		mdp = os.path.join(src, self.distinfo_name, "metadata.json")
		with open(mdp, "r") as fin:
			desc = json.load(fin).get("summary", "???")
		
		for command, definition in parser.items(section="console_scripts"):
			# name, loc = definition.replace(" ", "").split("=")
			modname, funcname = definition.split(":")
			if not command.endswith(".py"):
				command += ".py"
			path = create_command(
				command,
				(u"""'''%s'''
from %s import %s

if __name__ == "__main__":
    %s()
""" % (desc, modname, funcname, funcname)).encode("utf-8"))
			files_installed.append(path)
		return files_installed


class WheelInfoHandler(BaseHandler):
	"""Handler for wheel informations."""
	name = "WHEEL information checker"
	supported_major_versions = [1]
	supported_versions = ["1.0"]
	
	def handle_install(self, src, dest):
		wtxtp = os.path.join(src, self.distinfo_name, "WHEEL")
		with open(wtxtp, "r") as fin:
			for line in fin:
				line = line.replace("\r", "").replace("\n", "")
				ki = line.find(":")
				key = line[:ki]
				value = line[ki+2:]
				
				if key.lower() == "wheel-version":
					major, minor = value.split(".")
					major, minor = int(major), int(minor)
					if major not in self.supported_major_versions:
						raise WheelError("Wheel major version is incompatible!")
					if value not in self.supported_versions:
						print("WARNING: unsupported minor version: " + str(value))
					self.wheel.version = (major, minor)
				
				elif key.lower() == "generator":
					if self.verbose:
						print("Wheel generated by: " + value)
		return []


class DependencyHandler(BaseHandler):
	"""
	Handler for the dependencies.
	"""
	name = "dependency handler"
	
	def handle_install(self, src, dest):
		metap = os.path.join(src, self.distinfo_name, "metadata.json")
		if not os.path.exists(metap):
			if self.verbose:
				print("Warning: could not find 'metadata.json', can not detect dependencies!")
			return
		with open(metap, "r") as fin:
			content = json.load(fin)
		dependencies = content.get("run_requires", [{"requires": []}])[0]["requires"]
		self.wheel.dependencies += dependencies
	
		
# list of default handlers
DEFAULT_HANDLERS = [
	WheelInfoHandler,
	DependencyHandler,
	TopLevelHandler,
	ConsoleScriptsHandler,
	]


class Wheel(object):
	"""class for installing python wheels."""
	def __init__(self, path, handlers=DEFAULT_HANDLERS, verbose=False):
		self.path = path
		self.verbose = True
		self.filename = os.path.basename(self.path)
		self.handlers = [handler(self, self.verbose) for handler in handlers]
		self.version = None  # to be set by handler
		self.dependencies = []  # to be set by handler
		
		if not wheel_is_compatible(self.filename):
			raise WheelError("Incompatible wheel: {p}!".format(p=self.filename))
		
	def install(self, targetdir):
		"""
		Install the wheel into the target directory.
		Return (files_installed, dependencies)
		"""
		if self.verbose:
			print("Extracting wheel..")
		tp = self.extract_into_temppath()
		if self.verbose:
			print("Extraction finished, running handlers...")
		try:
			files_installed = []
			for handler in self.handlers:
				if hasattr(handler, "handle_install"):
					if self.verbose:
						print("Running handler '{h}'...".format(
							h=getattr(handler, "name", "<unknown>"))
							)
					tfi = handler.handle_install(tp, targetdir)
					if tfi is not None:
						files_installed += tfi
		finally:
			if self.verbose:
				print("Cleaning up...")
			if os.path.exists(tp):
				shutil.rmtree(tp)
		return (files_installed, self.dependencies)
	
	def extract_into_temppath(self):
		"""
		Extract the wheel into a temporary directory.
		Return the path of the temporary directory.
		"""
		p = os.path.join(tempfile.gettempdir(), "wheel_tmp", self.filename)
		if not os.path.exists(p):
			os.makedirs(p)
		
		with zipfile.ZipFile(self.path, mode="r") as zf:
			zf.extractall(p)
		
		return p


if __name__ == "__main__":
	# test script
	import sys
	fi, dep = Wheel(sys.argv[1], verbose=True).install(os.path.expanduser("~/Documents/site-packages/"))
	print("files installed: ")
	print(fi)
	print("dependencies:")
	print(dep)