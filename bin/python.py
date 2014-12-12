'''
Simulates a console call to python -m module|file [args]

Used for running standard library python modules such as:
SimpleHTTPServer, unittest and .py files.
[&] will run the module/file in the background

usage:
    python -m module_name [args]
    python python_file.py [args]
'''

import runpy
import sys
import threading
import ui
print sys.argv
run_as_thread = False
run_as_module = False

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

#Check for & to run as thread
if sys.argv[len(sys.argv)-1]=='&':
    sys.argv.pop()
    run_as_thread=True

#Check to run as module
if sys.argv[1] == '-m' and len(sys.argv)>=3:
    run_as_module = True
    sys.argv.pop(1)

#make sure enough args are present
if len(sys.argv) < 2:
    print 'Usage: python [-m] file|module [args] [&]'
    sys.exit()
    
module_name = str(sys.argv[1])
sys.argv.pop(1)

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
