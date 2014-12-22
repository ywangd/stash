'''
Simulates a console call to python -m module|file [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.
-b will run the module/file in the background

usage:
    python -m [-b] module_name [args]
    python [-b] python_file.py [args]
'''

import runpy
import sys
import threading
import ui
import argparse


class ModuleThread(threading.Thread):
    
    def __init__(self,module,name):
        self.is_module = module
        self.module_name = name
        threading.Thread.__init__(self)
    @ui.in_background    
    def run(self):
        try:
            if self.is_module:
                
                runpy.run_module(self.module_name, run_name='__main__')
            else:
                runpy.run_path(self.module_name, run_name='__main__')
        except Exception, e:
            print e
            

ap = argparse.ArgumentParser()
ap.add_argument('-m', '--module', action='store_true', default=False, help='run module')
ap.add_argument('-b', '--background', action='store_true', default=False, help='run as background thread')
ap.add_argument('name', help='file or module name')
ap.add_argument('args_to_pass', nargs=argparse.REMAINDER, help='args to pass')
args = ap.parse_args()

run_as_thread = args.background
run_as_module = args.module
module_name = str(args.name)

sys.argv = [sys.argv[0]] + args.args_to_pass

if run_as_module:
    try:
        #os.chdir('../..')
        if run_as_thread:
            ModuleThread(True,module_name).start()
        else:
            runpy.run_module(module_name, run_name='__main__')
    except ImportError, e:
        print 'ImportError: '+str(e)
else:
    try:
        if run_as_thread:
            ModuleThread(False,module_name).start()
        else:
            runpy.run_path(module_name, run_name='__main__')
    except Exception, e:
        print 'Error: '+ str(e)
