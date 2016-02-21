""" Package and compress (archive) files and directories """
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import sys
import argparse
import zipfile

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('zipfile', help='')
    ap.add_argument('list', nargs='+', help='')
    ap.add_argument('-v', '--verbose',
                    action='store_true',
                    help='be more chatty')
    ns = ap.parse_args(args)

    relroot = os.path.abspath(os.path.dirname(ns.zipfile))

    with zipfile.ZipFile(ns.zipfile, "w", zipfile.ZIP_DEFLATED) as outs:
        for path in ns.list:
            if os.path.isfile(path):
                if ns.verbose:
                    print(path)
                arcname = os.path.relpath(path, relroot)
                outs.write(path, arcname=arcname)

            elif os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    this_relroot = os.path.relpath(root, relroot)
                    # add directory (needed for empty dirs)
                    outs.write(root, arcname=this_relroot)
                    if ns.verbose:
                        print(this_relroot)
                    for f in files:
                        filename = os.path.join(root, f)
                        if os.path.isfile(filename):  # regular files only
                            if ns.verbose:
                                print(filename)
                            arcname = os.path.join(this_relroot, f)
                            outs.write(filename, arcname=arcname)


if __name__ == '__main__':
    main(sys.argv[1:])

