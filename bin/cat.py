#!/usr/bin/env python
########################################################################.......

"""Print the contents of the given files.
"""

from __future__ import print_function

import argparse
import sys
import fileinput

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", action="store", nargs="*", type=str,
                   help="one or more files to be printed")
    ns = p.parse_args(args)
    
    status = 0

    try:
        fileinput.close()  # in case it is not closed
        for line in fileinput.input(ns.files):
            print(line, end='')
    except Exception as e:
        print(str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
