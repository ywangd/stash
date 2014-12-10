import os
import sys
import fileinput
import argparse

import clipboard

ap = argparse.ArgumentParser()
ap.add_argument('file', nargs='?', help='the file to be pasted')
args = ap.parse_args()

thefile = args.file if args.file else None

if thefile is not None and os.path.isdir(thefile):
    print '%s: Is a directory' % thefile

else:
    if thefile is None:
        print clipboard.get()
    else:
        try:
            with open(thefile, 'w') as outs:
                outs.write(clipboard.get())
        except IOError:
            print '%s: cannot open for writing' % thefile
