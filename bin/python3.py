"""
Simulates a console call to python3 [-m module][-c cmd] [file] [args]

Used for running standard library python3 modules such as:
unittest and .py files.

Can also be used to run a script in the background, such as a server, with the bash character & at the end.
usage:
    python3
    python3 -m module_name [args]
    python3 -c command
    python3 python_file.py [args]
"""
# check for py2/3
_stash = globals()["_stash"]
if not _stash.PY3:
	print(
		_stash.text_color(
			"You are running StaSh in python 2.\nRunning python3 from python 2 is not (yet) supported.\nPlease use the 'python' command instead.",
			"red",
			)
		)
	import sys
	sys.exit(1)

import runpy
import sys
import argparse
import code
import builtins


args = sys.argv[1:]

passing_h = False
if '-h' in args and len(args) > 1:
    args.remove('-h')
    passing_h = True

ap = argparse.ArgumentParser()

group = ap.add_mutually_exclusive_group()
group.add_argument('-m', '--module',
                   action='store', default=None,
                   help='run module')
group.add_argument('-c', '--cmd',
                   action='store', default=None,
                   help='program passed in as string (terminates option list)')

ap.add_argument('args_to_pass',
                metavar='[file] args_to_pass',
                default=[],
                nargs=argparse.REMAINDER,
                help='Python script and arguments')

ns = ap.parse_args(args)
if passing_h:
    ns.args_to_pass.append('-h')

if ns.module:
    sys.argv = [ns.module] + ns.args_to_pass
    try:
        runpy.run_module(ns.module, run_name='__main__')
    except ImportError as e:
        print('ImportError: ' + str(e))
        sys.exit(1)
    sys.exit(0)

elif ns.cmd:
    exec(ns.cmd)
    sys.exit(0)

else:
    if ns.args_to_pass:
        sys.argv = ns.args_to_pass
        try:
            runpy.run_path(str(sys.argv[0]), run_name='__main__')
        except Exception as e:
            print('Error: ' + str(e))
    else:
        locals = {
            '__name__': '__main__',
            '__doc__': None,
            '__package__': None,
            '__debug__': True,
            '__builtins__': builtins,
            '_stash': _stash,
        }
        code.interact(local=locals)