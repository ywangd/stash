#!/usr/bin/env python
########################################################################.......

"""Print the contents of the given files.
"""

from __future__ import print_function

import argparse
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", action="store", nargs="*", type=str,
                   help="one or more files to be printed")
    ns = p.parse_args(args)
    
    status = 0
    
    if len(ns.file) > 0:
        for filename in ns.file:
            try:
                with open(filename, "rb") as f:
                    buf = "foo"
                    while buf:
                        # stdout doesn't like writing \x00 bytes, however this
                        # fix might have unwanted effects when cat is used in
                        # a pipe, so it's disabled for now
                        ##buf = f.read(1024).replace(b"\x00", b"")
                        ##print(buf.decode("ascii", errors="replace"), end="")
                        buf = f.read(1024)
                        print(buf, end="")
            except Exception as err:
                print("cat: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
                status = 1
    else:
        print(raw_input())
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
