#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Update the modification times of the given files, and create them if
they do not yet exist.
"""

import argparse
import os
import sys
from pathlib import Path


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-c", "--no-create", action="store_true", help="do not create nonexistant files"
    )
    p.add_argument(
        "file", type=Path, action="store", nargs="+", help="one or more files to be touched"
    )
    ns = p.parse_args(args)

    try:
        for filename in ns.file:
            if not filename.exists() and not ns.no_create:
                open(filename, "wb").close()
            os.utime(filename, None)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print("touch: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
