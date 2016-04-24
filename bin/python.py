"""
Simulates a console call to python [-m module][-c cmd] [file] [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.

Can also be used to run a script in the background, such as a server, with the bash character & at the end.
usage:
    python
    python -m module_name [args]
    python python_file.py [args]
    python -c cmd
"""

import runpy
import sys
import argparse
import code
import __builtin__

ap = argparse.ArgumentParser()
ap.add_argument('-m', '--module', action='store', default=None, help='run module')
ap.add_argument('-c', '--cmd', action='store', default=None, help='program passed in as string (terminates option list)')
ap.add_argument('file', action='store', default=None, help='program read from script file (terminates option list)', nargs='?')#,required=False)
ap.add_argument('args_to_pass', nargs=argparse.REMAINDER, help='arguments passed to program in sys.argv[1:]')
args = ap.parse_args()

sys.argv = [sys.argv[0]] + args.args_to_pass

if (args.module is not None) and (args.cmd is not None):
	print 'Error: Please only pass either "-c" or "-m", but not both!'
	sys.exit(1)
elif args.module is not None:
	try:
		runpy.run_module(str(args.module), run_name='__main__')
	except ImportError, e:
		print 'ImportError: ' + str(e)
		sys.exit(1)
	sys.exit(0)

elif args.cmd is not None:
	exec args.cmd
	sys.exit(0)

elif args.file is not None:
	try:
		runpy.run_path(str(args.file), run_name='__main__')
	except Exception, e:
		print 'Error: ' + str(e)
else:
	locals={
	'__name__':'__main__',
	'__doc__':None,
	'__package__':None,
	'__builtins__':__builtin__,#yes, __builtins__
	}
	code.interact(local=locals)
