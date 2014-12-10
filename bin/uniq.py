import os
import sys
import fileinput
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('file', nargs='?', help='the file to be uniqued. must be sorted first.')
args = ap.parse_args()

thefile = args.file if args.file else None

if thefile is not None and os.path.isdir(thefile):
    print '%s: Is a directory' % thefile

else:
    try:
        fileinput.close()  # in case it is not closed
        prev_line = None
        lines = []
        for line in fileinput.input(thefile):
            if prev_line is None or line != prev_line:
               lines.append(line)
            prev_line = line

        print ''.join(lines)
    finally:
        fileinput.close()