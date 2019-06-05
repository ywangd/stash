"""Print standard input or files, omitting repeated lines"""
from __future__ import print_function

import os
import sys
import fileinput
import argparse


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        'files',
        nargs='*',
        help='files to unique (must be sorted first)')
    ns = ap.parse_args(args)

    def _print(lines):
        if lines is not None:
            print(''.join(lines))

    fileinput.close()  # in case it is not closed
    try:
        prev_line = None
        lines = None
        for line in fileinput.input(
                ns.files, openhook=fileinput.hook_encoded("utf-8")):
            if fileinput.isfirstline():
                _print(lines)
                lines = []
                prev_line = None
            if prev_line is None or line != prev_line:
                lines.append(line)
            prev_line = line

        _print(lines)

    finally:
        fileinput.close()


if __name__ == '__main__':
    main(sys.argv[1:])
