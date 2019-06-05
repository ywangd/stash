#!/usr/bin/env python
# .......

"""Print the contents of the given files.
"""

from __future__ import print_function

import argparse
import string
import sys
import fileinput


def filter_non_printable(s):
    return ''.join([c if c.isalnum() or c.isspace()
                    or c in string.punctuation else ' ' for c in s])


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", action="store", nargs="*",
                   help="files to print")
    ns = p.parse_args(args)

    status = 0

    fileinput.close()  # in case it is not closed
    try:
        for line in fileinput.input(ns.files,
                                    openhook=fileinput.hook_encoded("utf-8")):
            print(filter_non_printable(line), end='')
    except Exception as e:
        print('cat: %s' % str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
