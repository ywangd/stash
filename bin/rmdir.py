#! python2
# -*- coding: utf-8 -*-
# StaSh utility - Dutcho, 17 Apr 2017
"""Remove empty directory"""

import argparse
import os
import sys
from pathlib import Path


def rmdir(paths: list[Path], verbose: bool):
    """
    Removes empty directories specified in the paths list.
    """
    for path in paths:
        try:
            os.rmdir(path)
            if verbose:
                print(f"Removed directory '{path}'")
        except OSError as e:
            # os.rmdir will raise OSError if the directory is not empty
            # or if it doesn't exist, which we handle here.
            print(f"rmdir: failed to remove '{path}': {e.strerror}", file=sys.stderr)


def main(args):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog='Use "rm -r" to remove non-empty directory tree'
    )
    parser.add_argument(
        "dir",
        help="directories to remove",
        nargs="+",
        type=Path
    )
    parser.add_argument(
        "-v", "--verbose",
        help="display info for each processed directory",
        action="store_true"
    )
    ns = parser.parse_args(args)
    try:
        rmdir(ns.dir, ns.verbose)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
