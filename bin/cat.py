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

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("files", action="store", nargs="*",
                   help="files to print")
    ns = p.parse_args(args)

    status = 0

    fileinput.close()  # in case it is not closed
    try:
        for line in fileinput.input(ns.files, mode='rb'):
            line = line.decode('utf-8', 'ignore')
            print(line, end='')
    except Exception as e:
        print('cat :%s' % str(e))
        status = 1
    finally:
        fileinput.close()

    sys.exit(status)

if __name__ == "__main__":
    main(sys.argv[1:])
