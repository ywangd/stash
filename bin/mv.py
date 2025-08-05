#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Move (rename) a file or directory to a new name, or into a new
directory. Multiple source files may be specified if the destination is
an existing directory.
"""

from __future__ import print_function

import argparse
import os
import shutil
import sys


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "src", action="store", nargs="+", help="one or more source files or folders"
    )
    p.add_argument("dest", action="store", help="the destination name or folder")
    ns = p.parse_args(args)

    status = 0

    if len(ns.src) > 1:
        # Multiple source files
        if os.path.exists(ns.dest):
            # Destination must exist...
            if os.path.isdir(ns.dest):
                # ...and be a directory
                for src in ns.src:
                    try:
                        # Attempt to move every source into destination
                        shutil.move(src, ns.dest)
                    except Exception as err:
                        print(
                            "mv: {}: {!s}".format(type(err).__name__, err),
                            file=sys.stderr,
                        )
                        status = 1
            else:
                print("mv: {}: not a directory".format(ns.dest), file=sys.stderr)
        else:
            print("mv: {}: no such file or directory".format(ns.dest), file=sys.stderr)
            status = 1
    else:
        # Single source file
        src = ns.src[0]
        if os.path.exists(src):
            # Source must exist
            if not os.path.isfile(ns.dest):
                # Python will rename source if it doesn't exists
                # And will move source into destination if it is a directory
                try:
                    shutil.move(src, ns.dest)
                except Exception as err:
                    print(
                        "mv: {}: {!s}".format(type(err).__name__, err), file=sys.stderr
                    )
                    status = 1
            else:
                # Won't overwrite unasked
                print("mv: {}: file exists".format(ns.dest), file=sys.stderr)
        else:
            print("mv: {}: no such file or directory".format(src), file=sys.stderr)
            status = 1

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
