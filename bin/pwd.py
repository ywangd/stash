#!/usr/bin/env python
########################################################################.......

"""Print the current working directory.
"""

from __future__ import print_function

import argparse
import os
import sys

_stash = globals()['_stash']
collapseuser = _stash.libcore.collapseuser

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-b", "--basename", action="store_true",
                   help="show basename only")
    ns = p.parse_args(args)
    
    status = 0
    
    try:
        print(os.path.basename(os.getcwd()) if ns.basename else collapseuser(os.getcwd()))
    except Exception as err:
        print("pwd: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        status = 1
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
