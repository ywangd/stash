#!/usr/bin/env python
########################################################################.......

"""Change the current working directory.
"""

from __future__ import print_function

import argparse
import os
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dir", action="store", nargs="*",
                   default=[os.environ["HOME2"]], type=str,
                   help="the new working directory")
    ns = p.parse_args(args)
    
    status = 0
    
    try:
       #chdir does not raise exception until listdir is called, so check for access here
       if os.access(ns.dir[0],os.R_OK):
          os.chdir(ns.dir[0])
       else:
          print('cd: {} access denied'.format(ns.dir[0]))
    except Exception as err:
        print("cd: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        status = 1
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])