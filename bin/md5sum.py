'''
md5sum - Get md5 hash of a file

usage: md5sum.py [-h] [-c] file

positional arguments:
  file         File to get md5sum or file contailing a list of hashes and files

optional arguments:
  -h, --help   show this help message and exit
  -c, --check  Check a file with md5 values and files for a match. format:
               md5_hash filename
               md5_hash filename
               etc.
'''
import argparse
from Crypto.Hash import MD5
import re

def get_md5(fileobj):
    h = MD5.new()
    chunk_size = 8192
    while True:
        chunk = fileobj.read(chunk_size)
        if len(chunk) == 0:
            break
        h.update(chunk)
    return h.hexdigest()
    
def check_list(filename):
    with open(filename,'r') as f:
        for line in f:
            match = re.match(r'(\w+) ([\w.-_]+)',line)
            try:
                with open(match.group(2),'rb') as f1:
                    if match.group(1) == get_md5(f1):
                        print match.group(2)+': Pass'
                    else:
                        print match.group(2)+': Fail'
            except:
                print '''Invalid file to check. 
                Format:
                    md5_hash file_path
                    md5_hash file_path
                    '''
                break
    
        
ap = argparse.ArgumentParser()
ap.add_argument('-c','--check',action='store_true',default=False,
                help='''Check a file with md5 values and files for a match. format: md5_hash filename''')
ap.add_argument('file',action='store',help='File to get md5sum or file contailing a list of hashes and files')
args = ap.parse_args()

if args.check:
    check_list(args.file)
else:
    with open(args.file,'rb') as f:
        print get_md5(f)
