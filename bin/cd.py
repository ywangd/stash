#!/usr/bin/env python
# .......

"""Change the current working directory.
"""

from __future__ import print_function

import argparse
import os
import sys


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dir", action="store", nargs="?",
                   default=os.environ["HOME2"],
                   help="the new working directory")
    ns = p.parse_args(args)

    status = 0

    try:
        if os.path.exists(ns.dir):
            if os.path.isdir(ns.dir):
                # chdir does not raise exception until listdir is called, so
                # check for access here
                if os.access(ns.dir, os.R_OK):
                    os.chdir(ns.dir)
                else:
                    print('cd: {} access denied'.format(ns.dir))
            else:
                print('cd: %s: Not a directory' % ns.dir)
        else:
            print ('cd: %s: No such file or directory' % ns.dir)
    except Exception as err:
        print("cd: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        status = 1

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
