#! python2
# -*- coding: utf-8 -*-
# StaSh utility - Dutcho, 17 Apr 2017

'''Remove empty directory'''

from __future__ import print_function

import argparse
import os
import sys


def rmdir(dirnames, verbose=False):
    for dirname in dirnames:
        try:
            os.rmdir(dirname)
            if verbose:
                print('Removed directory {!r}'.format(dirname))
        except OSError as e:
            print('Cannot remove directory {!r}: {}'.format(dirname, e), file=sys.stderr)

# --- main


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Use "rm -r" to remove non-empty directory tree')
    parser.add_argument(
        'dir',
        help='directories to remove',
        action='store',
        nargs='+')
    parser.add_argument(
        '-v',
        '--verbose',
        help='display info for each processed directory',
        action='store_true')
    ns = parser.parse_args(args)
    rmdir(ns.dir, ns.verbose)


if __name__ == "__main__":
    main(sys.argv[1:])
