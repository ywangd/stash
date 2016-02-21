"""
Simulates a console call to python -m module|file [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.

Can also be used to run a script in the background, such as a server, with the bash character & at the end.
usage:
    python -m module_name [args]
    python python_file.py [args]
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import runpy
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('-m', '--module', action='store_true', default=False, help='run module')
ap.add_argument('-c', '--cmd', action='store_true', default=False, help='program passed in as string')
ap.add_argument('name', help='file or module name')
ap.add_argument('args_to_pass', nargs=argparse.REMAINDER, help='args to pass')
args = ap.parse_args()

sys.argv = [sys.argv[0]] + args.args_to_pass

if args.module:
    try:
        runpy.run_module(str(args.name), run_name='__main__')
    except ImportError as e:
        print('ImportError: ' + str(e))

elif args.cmd:
    exec(args.name)

else:
    try:
        runpy.run_path(str(args.name), run_name='__main__')
    except Exception as e:
        print('Error: ' + str(e))
