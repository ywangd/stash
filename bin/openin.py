#!/usr/bin/env python
########################################################################.......

"""Open file in an external app.
"""

from __future__ import print_function

import argparse
import console
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", action="store", help="file to open")
    ns = p.parse_args(args)
    
    status = 0
    
    if console.open_in(ns.file) is None:
        status = 1
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
