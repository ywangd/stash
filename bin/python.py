'''
Simulates a console call to python -m module|file [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.

Can also be used to run a script in the background, such as a server, with the bash character & at the end.
usage:
    python -m module_name [args]
    python python_file.py [args]
'''

import runpy
import sys
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('-m', '--module', action='store_true', default=False, help='run module')
ap.add_argument('name', help='file or module name')
ap.add_argument('args_to_pass', nargs=argparse.REMAINDER, help='args to pass')
args = ap.parse_args()

module_name = str(args.name)

sys.argv = [sys.argv[0]] + args.args_to_pass

if args.module:
    try:
        runpy.run_module(module_name, run_name='__main__')
    except ImportError, e:
        print 'ImportError: '+str(e)
else:
    try:
        runpy.run_path(module_name, run_name='__main__')
    except Exception, e:
        print 'Error: '+ str(e)
