#!/usr/bin/env python
########################################################################.......

"""Open file in Quick Look.
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
    
    if "_stash" in globals():
        print("quicklook: This command cannot be used inside stash due to conflicts with the ui module.", file=sys.stderr)
        status = 1
    else:
        console.quicklook(ns.file)
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
