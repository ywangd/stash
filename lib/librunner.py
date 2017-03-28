"""module for running a script in a specific python version"""
import os
import sys
import ctypes
import base64
import pickle


# TODO:
# - RPC to _stash (if possible)
# - killing mechanism

EXE_DIR = os.path.dirname(sys.executable)
OLD_PY2_FRAMEWORK = "PythonistaKit"
NEW_PY2_FRAMEWORK = "Py2Kit"

CODE_TEMPLATE = """#Py3 preperation template
import os
import sys
import pickle
import base64
import traceback

CWD = "{cwd}"
CODE = base64.b64decode("{b64c}")  # use b64 to prevent syntax errors
STDIN_FD = {stdin}
STDOUT_FD = {stdout}
STDERR_FD = {stderr}

# prepare I/O
sys.stdin = open(STDIN_FD, "r")
sys.stdout = open(STDOUT_FD, "w")
sys.stderr = open(STDERR_FD, "w")

# prepare env, cwd ...
os.chdir(CWD)

# prepare scope
c_globals = pickle.loads(base64.b64decode("{globals}"))
c_locals = pickle.loads(base64.b64decode("{locals}"))

# execute
try:
	exec(CODE, c_globals, c_locals)
except Exception as e:
	# only print traceback, so we can close sys.std*
	traceback.print_exc(file=sys.stderr)
finally:
	sys.stdin.close()
	sys.stdout.close()
	sys.stderr.close()
"""

def get_dll(version):
	"""returns a PyDLL for a specific python version"""
	if version == 2:
		for name in (OLD_PY2_FRAMEWORK, NEW_PY2_FRAMEWORK):
			path = os.path.join(EXE_DIR, "Frameworks", name + ".framework", name)
			if os.path.exists(path):
				return ctypes.PyDLL(path)
		raise RuntimeError("Could not load any Python 2 Framework!")
	elif version == 3:
		return ctypes.pythonapi
	else:
		raise ValueError("Unknown Python version: '{v}'!".format(v=version))


def exec_string(dll, s):
	"""execute a string with the dll"""
	state = dll.PyGILState_Ensure()
	dll.PyRun_SimpleString(s)
	dll.PyGILState_Release(state)

def exec_string_with_io(dll, s, cwd=None, globals={}, locals={}):
	"""executes string s using dll and return stdin, stdout, stderr"""
	if cwd is None:
		cwd = os.getcwd()
	inr, inw = os.pipe()
	outr, outw = os.pipe()
	excr, excw = os.pipe()
	stdin = os.fdopen(inw, "w")
	stdout = os.fdopen(outr, "r")
	stderr = os.fdopen(excr, "r")
	filled_t = CODE_TEMPLATE.format(
		b64c=base64.b64encode(s),
		cwd=cwd,
		stdin=inr,
		stdout=outw,
		stderr=excw,
		globals=base64.b64encode(pickle.dumps(globals)),
		locals=base64.b64encode(pickle.dumps(locals)),
		)
	exec_string(dll, filled_t)
	return stdin, stdout, stderr


def _test():
	# test code. status message are UPPERCASE to see test starts/end easier
	dll3 = get_dll(3)
	# 1. syntax error print
	sys.stdout.write("STARTING SYNTAX ERROR TEST PY3...\n")
	i, o, e = exec_string_with_io(dll3, "print 'this should be an error in py3'")
	sys.stdout.write("READING STDOUT (expected empty)...\n")
	sys.stdout.write(o.read(2048)+"\n")
	sys.stdout.write("READING STDERR (expected traceback)...\n")
	sys.stdout.write(e.read(4096)+"\n")
	sys.stdout.write("CLOSING I/O...\n")
	i.close()
	o.close()
	e.close()
	sys.stdout.write("\nSYNTAX ERROR TEST FINISHED\n")
	# 2. echo test
	sys.stdout.write("STARTING ECHO TEST...\n")
	i, o, e = exec_string_with_io(
		dll3,
		"print(input('Hello, what is your name?').uppercase())",
		)
	sys.stdout.write("READING STDOUT (expected prompt)...\n")
	sys.stdout.write(o.read(2048)+"\n")
	sys.stdout.write("READING STDERR (expected empty)...\n")
	sys.stdout.write(e.read(4096)+"\n")
	sys.stdout.write("PLEASE ENTER A STRING TO SEND TO STDIN:\n")
	i.write(sys.stdin.readline())
	sys.stdout.write("CLOSING I/O...\n")
	i.close()
	o.close()
	e.close()
	sys.stdout.write("\nSYNTAX ERROR TEST FINISHED\n")


if __name__ == "__main__":
	_test()