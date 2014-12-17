#!/usr/bin/env python
########################################################################.......

"""Create a new directory. The parent directory must already exist,
unless -p is specified.
"""

from __future__ import print_function

import argparse
import os
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-p", "--parents", action="store_true",
                   help="create parent directories as necessary")
    p.add_argument("dir", action="store", nargs="+",
                   help="the directory to be created")
    ns = p.parse_args(args)
    
    status = 0
    
    for dir in ns.dir:
        try:
            (os.makedirs if ns.parents else os.mkdir)(dir)
        except Exception as err:
            print("mkdir: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
            status = 1
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
