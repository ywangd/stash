import os
import sys
import fileinput
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('file', nargs='?', help='the file to be sorted')
ap.add_argument('-r', '--reverse', action='store_true', default=False,
                help='reverse the result of comparisons')
args = ap.parse_args()

thefile = args.file if args.file else None

if thefile is not None and os.path.isdir(thefile):
    print '%s: Is a directory' % thefile

else:
    try:
        fileinput.close()  # in case it is not closed
        lines = sorted(line for line in fileinput.input(thefile))
        if args.reverse:
            lines = lines[::-1]

        print ''.join(lines)

    finally:
        fileinput.close()