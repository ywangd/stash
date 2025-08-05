# -*- coding: utf-8 -*-
"""
Get sha256 hash of a file or string.

usage: sha256sum.py [-h] [-c] [file [file ...]]

positional arguments:
  file         String or file to hash.

optional arguments:
  -h, --help   show this help message and exit
  -c, --check  Check a file with sha256 hashes and file names for a match.
               format:
               sha256_hash filename
               sha256_hash filename
               etc.
"""

from __future__ import print_function

import argparse
import os
import re
import sys

import six

from Crypto.Hash import SHA256


def get_hash(fileobj):
    h = SHA256.new()
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
        match = re.match(r"(\w+)[ \t]+(.+)", line)
        try:
            with open(match.group(2), "rb") as f1:
                if match.group(1) == get_hash(f1):
                    print(match.group(2) + ": Pass")
                else:
                    print(match.group(2) + ": Fail")
                    correct = False
        except:
            print("Invalid format.")
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
ap.add_argument(
    "-c",
    "--check",
    action="store_true",
    default=False,
    help="""Check a file with sha256 hashes and file names for a match. format: hash filename""",
)
ap.add_argument("file", action="store", nargs="*", help="String or file to hash.")
args = ap.parse_args(sys.argv[1:])

if args.check:
    if args.file:
        s = True
        for arg in args.file:
            if os.path.isfile(arg):
                s = s and check_list(open(arg))
    else:
        s = check_list(make_file(sys.stdin.read()))
    if s:
        sys.exit(0)
    else:
        sys.exit(1)

else:
    if args.file:
        for arg in args.file:
            if os.path.isfile(arg):
                with open(arg, "rb") as f:
                    print(get_hash(f) + " " + arg)
            elif arg == "-":
                print(get_hash(make_file(sys.stdin.read())))
            else:
                print(get_hash(make_file(arg)))
    else:
        print(get_hash(make_file(sys.stdin.read())))
