from __future__ import print_function

import argparse
import os
import sys

import clipboard

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='?', help='the file to be pasted')
    ns = ap.parse_args(args)
    
    status = 0
    
    if ns.file:
        if os.path.exists(ns.file):
            print("paste: {}: file exists".format(ns.file), file=sys.stderr)
            status = 1
        else:
            try:
                with open(ns.file) as f:
                    f.write(clipboard.get())
            except Exception as err:
                print("paste: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    else:
        print(clipboard.get())
    
    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
