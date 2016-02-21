#!/usr/bin/env python
########################################################################.......

"""Print the contents of the given files.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import sys
import fileinput
def filter_non_printable(s):
    return ''.join([c if (31 < ord(c) < 127 or c in "\n\r\t\b") else ' ' for c in s])
    
def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", action="store", nargs="*",
                   help="files to print")
    ns = p.parse_args(args)

    status = 0

    fileinput.close()  # in case it is not closed
    try:
        for line in fileinput.input(ns.files):
            print(filter_non_printable(line), end='')
    except Exception as e:
        print('cat :%s' % str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
