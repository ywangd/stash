"""Copy one or more files to the system clipboard"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse
import fileinput
import os
import sys

import clipboard

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('file', nargs='*', help='one or more files to be copied')
    ns = ap.parse_args(args)
    
    fileinput.close()  # in case it is not closed
    try:
        clipboard.set(''.join(line for line in fileinput.input(
            ns.file, openhook=fileinput.hook_encoded('utf-8'))))
    except Exception as err:
        print("pbcopy: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    finally:
        fileinput.close()

if __name__ == "__main__":
    main(sys.argv[1:])
