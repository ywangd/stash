# -*- coding: utf-8 -*-
"""
Remove (delete) files and directories.

usage: rm.py [-h] [-r] [-i] [-f] [-v] paths [paths ...]

positional arguments:
  paths              files or directories to delete

optional arguments:
  -h, --help         show this help message and exit
  -r, --recursive    remove directory and its contents recursively
  -i, --interactive  prompt before every removal
  -f, --force        attempt to delete without confirmation or warning due to
                     permission or file existence (override -i)
  -v, --verbose      explain what is being done
"""
from __future__ import print_function

import os
import sys
import shutil
from argparse import ArgumentParser

from six.moves import input


def main(args):
    ap = ArgumentParser()
    ap.add_argument(
        '-r',
        '--recursive',
        action="store_true",
        default=False,
        help='remove directory and its contents recursively'
    )
    ap.add_argument('-i', '--interactive', action="store_true", default=False, help='prompt before every removal')
    ap.add_argument(
        '-f',
        '--force',
        action='store_true',
        default=False,
        help='attempt to delete without confirmation or warning due to permission or file existence (override -i)'
    )
    ap.add_argument('-v', '--verbose', action="store_true", default=False, help='explain what is being done')
    ap.add_argument('paths', action="store", nargs='+', help='files or directories to delete')

    ns = ap.parse_args(args)

    #setup print function
    if ns.verbose:

        def printp(text):
            print(text)
    else:

        def printp(text):
            pass

    if ns.interactive and not ns.force:

        def prompt(file):
            result = input('Delete %s? [Y,n]: ' % file)
            if result == 'Y' or result == 'y':
                return True
            else:
                return False
    else:

        def prompt(file):
            return True

    for path in ns.paths:
        if (os.path.isfile(path) or
            os.path.islink(path)):
            if prompt(path):
                try:
                    os.remove(path)
                    printp('%s has been deleted' % path)
                except Exception as e:
                    if not ns.force:
                        print('%s: unable to remove' % path)
                        printp(e)

        elif os.path.isdir(path) and ns.recursive:
            if prompt(path):
                try:
                    shutil.rmtree(path)
                    printp('%s has been deleted' % path)
                except Exception as e:
                    if not ns.force:
                        print('%s: unable to remove' % path)
                        printp(e)

        elif os.path.isdir(path):
            print('%s: is a directory' % path)
        else:
            if not ns.force:
                print('%s: does not exist' % path)


if __name__ == '__main__':
    main(sys.argv[1:])
