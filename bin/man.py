'''
Lists docstrings for file

usage: man [file]
'''
import sys
import os
import re

path = os.path.abspath(os.path.dirname(__file__))
modules =  os.listdir(path)
module_dict = {}
for mod in modules:
    module_dict[re.sub(r'\.\w*','',mod)]=mod
    
if len(sys.argv) == 1:
    for mod in module_dict.keys():
        print mod
        #print mod.replace('.*','',mod)
if len(sys.argv) >1:
    search_str = sys.argv[1]
    output = ''
    expr = re.compile(r"'''(.*)'''",re.S)
    with open(path+'/'+module_dict[search_str],'r') as f:
        out = f.read()
        try:
            output = 'Man page for %s\n%s'%(search_str,expr.search(out).group(1))
        except:
            output = '*No man page found*'
    print output
        
