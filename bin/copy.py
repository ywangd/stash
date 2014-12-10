import os
import sys
import fileinput
import argparse

import clipboard

ap = argparse.ArgumentParser()
ap.add_argument('file', nargs='?', help='the file to be copied')
args = ap.parse_args()

thefile = args.file if args.file else None

if thefile is not None and os.path.isdir(thefile):
    print '%s: Is a directory' % thefile

else:
    try:
        fileinput.close()  # in case it is not closed
        clipboard.set(''.join(line for line in fileinput.input(thefile)))
    finally:
        fileinput.close()