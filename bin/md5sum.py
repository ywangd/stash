'''
Get md5 hash of a file or string.

usage: md5sum.py [-h] [-c] [file [file ...]]

positional arguments:
  file         String or file to hash.

optional arguments:
  -h, --help   show this help message and exit
  -c, --check  Check a file with md5 hashes and file names for a match.
               format:
               md5_hash filename
               md5_hash filename
               etc.
'''
from __future__ import print_function

import argparse
import os
import re
import sys

import six

from Crypto.Hash import MD5


def get_hash(fileobj):
    h = MD5.new()
    chunk_size = 8192
    while True:
        chunk = fileobj.read(chunk_size)
        if len(chunk) == 0:
            break
        h.update(chunk)
    return h.hexdigest()


def check_list(fileobj):
    correct = True
    for line in fileobj:
        if line.strip() == "":
            continue
        match = re.match(r'(\w+)[ \t]+(.+)', line)
        try:
            with open(match.group(2), 'rb') as f1:
                if match.group(1) == get_hash(f1):
                    print(match.group(2) + ': Pass')
                else:
                    print(match.group(2) + ': Fail')
                    correct = False
        except BaseException:
            print('Invalid format.')
            correct = False
    return correct


def make_file(txt):
    f = six.BytesIO()
    if isinstance(txt, six.binary_type):
        f.write(txt)
    else:
        f.write(txt.encode("utf-8"))
    f.seek(0)
    return f


ap = argparse.ArgumentParser()
ap.add_argument('-c', '--check', action='store_true', default=False,
                help='''Check a file with md5 hashes and file names for a match. format: hash filename''')
ap.add_argument(
    'file',
    action='store',
    nargs='*',
    help='String or file to hash.')
args = ap.parse_args(sys.argv[1:])

if args.check:
    if args.file:
        for arg in args.file:
            if os.path.isfile(arg):
                s = check_list(open(arg))
                if s:
                    sys.exit(0)
                else:
                    sys.exit(1)
    else:
        check_list(make_file(sys.stdin.read()))
else:
    if args.file:
        for arg in args.file:
            if os.path.isfile(arg):
                # hash file
                with open(arg, 'rb') as f:
                    print(get_hash(f) + ' ' + arg)
            elif arg == "-":
                # read from stdin
                print(get_hash(make_file(sys.stdin.read())))
            else:
                # hash arg
                # TODO: should we realy do this? It does not seem like normal
                # md5sum behavior
                print(get_hash(make_file(arg)))
    else:
        print(get_hash(make_file(sys.stdin.read())))
