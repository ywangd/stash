# -*- coding: utf-8 -*-
"""Sort standard input or given files to standard output"""
from __future__ import print_function
import os
import sys
import fileinput
import argparse


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*', help='files to sort')
    ap.add_argument('-r', '--reverse', action='store_true', default=False,
                    help='reverse the result of comparisons')
    ns = ap.parse_args(args)

    def _print(lines):
        if lines is not None:
            lines = sorted(lines)
            if ns.reverse:
                lines = lines[::-1]
            print(''.join(lines))

    fileinput.close()  # in case it is not closed
    try:
        lines = None
        for line in fileinput.input(
                ns.files, openhook=fileinput.hook_encoded("utf-8")):
            if fileinput.isfirstline():
                _print(lines)
                lines = []
            lines.append(line)

        _print(lines)

    finally:
        fileinput.close()


if __name__ == '__main__':
    main(sys.argv[1:])
