#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Update the modification times of the given files, and create them if
they do not yet exist.
"""

from __future__ import print_function

import argparse
import os
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-c", "--no-create", action="store_true",
                   help="do not create nonexistant files")
    p.add_argument("file", action="store", nargs="+",
                   help="one or more files to be touched")
    ns = p.parse_args(args)
    
    status = 0
    
    for filename in ns.file:
        try:
            if not os.path.exists(filename) and not ns.no_create:
                open(filename, "wb").close()
            os.utime(filename, None)
        except Exception as err:
            print("touch: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
            status = 1
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
