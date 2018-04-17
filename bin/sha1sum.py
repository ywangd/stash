'''
Get sha1 hash of a file or string. 

usage: sha1sum.py [-h] [-c] [file [file ...]]

positional arguments:
  file         String or file to hash.

optional arguments:
  -h, --help   show this help message and exit
  -c, --check  Check a file with sha1 hashes and file names for a match.
               format:
               sha1_hash filename
               sha1_hash filename
               etc.
'''
from __future__ import print_function
import argparse
from Crypto.Hash import SHA
import re
import sys
import os
from six import StringIO

def get_hash(fileobj):
    h = SHA.new()
    chunk_size = 8192
    while True:
        chunk = fileobj.read(chunk_size)
        if len(chunk) == 0:
            break
        h.update(chunk)
    return h.hexdigest()
    
def check_list(fileobj):
    for line in fileobj:
        match = re.match(r'(\w+)[ \t]+(.+)',line)
        try:
            with open(match.group(2),'rb') as f1:
                if match.group(1) == get_hash(f1):
                    print(match.group(2)+': Pass')
                else:
                    print(match.group(2)+': Fail')
        except:
            print('Invalid format.')
                
def make_file(txt):
    f = StringIO()
    f.write(txt)
    f.seek(0)
    return f
    
ap = argparse.ArgumentParser()
ap.add_argument('-c','--check',action='store_true',default=False,
                help='''Check a file with sha1 hashes and file names for a match. format: hash filename''')
ap.add_argument('file',action='store',nargs='*',help='String or file to hash.')
args = ap.parse_args(sys.argv[1:])

if args.check:
    if args.file:
        for arg in args.file:
            if os.path.isfile(arg):
                check_list(open(arg))
    else:
        check_list(make_file(sys.stdin.read()))
else:
    if args.file:
        for arg in args.file:
            if os.path.isfile(arg):
                with open(arg,'rb') as f:
                    print(get_hash(f)+' '+arg)
            else:
                print(get_hash(make_file(arg)))
    else:
        print(get_hash(make_file(sys.stdin.read())))
        
    
