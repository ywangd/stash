""" Find files in specified paths
"""

import os
import sys
import argparse
import fnmatch


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='+', help='specify a file hierarchy for find to traverse')
    ap.add_argument('-n', '-name', '--name', dest='pattern',
                    nargs='?', help='pattern to match file names')
    ap.add_argument('-t', '-type', '--type',
                    nargs='?', help='specify the file type to match.\nf - regular file\nd - directory')
    ns = ap.parse_args(args)

    pattern = '*' if ns.pattern is None else ns.pattern
    ftype = ns.type

    names = []
    for pth in ns.paths:
        for root, dirs, files in os.walk(pth):
            if ftype is None or ftype == 'f':
                names.extend(os.path.join(root, name) for name in fnmatch.filter(files, pattern))
            if ftype is None or ftype == 'd':
                names.extend(os.path.join(root, name + '/') for name in fnmatch.filter(dirs, pattern))

    print '\n'.join(names)


if __name__ == "__main__":
    main(sys.argv[1:])