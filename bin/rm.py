# -*- coding: utf-8 -*-
"""
Remove (delete) files and directories.

usage: rm.py [-h] [-r] [-i] [-f] [-v] paths [paths ...]

positional arguments:
  paths              files or directories to delete

optional arguments:
  -h, --help         show this help message and exit
  -r, --recursive    remove directory and its contents recursively
  -i, --interactive  prompt before every removal
  -f, --force        attempt to delete without confirmation or warning due to
                     permission or file existence (override -i)
  -v, --verbose      explain what is being done
"""

import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path


def rm(path: Path, args):
    """
    Deletes a file or directory based on the provided arguments.
    """
    if not path.exists():
        if args.force:
            return  # Silently ignore non-existent paths
        print(f"rm: {path}: No such file or directory", file=sys.stderr)
        return

    # Handle directories
    if path.is_dir():
        if not args.recursive:
            print(f"rm: {path}: Is a directory", file=sys.stderr)
            return
        if args.interactive and not args.force:
            if input(f"rm: descend into directory '{path}'? [y/N] ").lower() != 'y':
                return

        # Recursive removal
        try:
            shutil.rmtree(path)
            if args.verbose:
                print(f"removed directory '{path}'")
        except OSError as e:
            print(f"rm: {path}: {e.strerror}", file=sys.stderr)
        return

    # Handle files
    if path.is_file():
        if args.interactive and not args.force:
            if input(f"rm: remove regular file '{path}'? [y/N] ").lower() != 'y':
                return

        # File removal
        try:
            os.remove(path)
            if args.verbose:
                print(f"removed '{path}'")
        except OSError as e:
            print(f"rm: {path}: {e.strerror}", file=sys.stderr)
        return


def main(args):
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("-r", "--recursive", action="store_true", help="remove directory and its contents recursively")
    ap.add_argument("-i", "--interactive", action="store_true", help="prompt before every removal")
    ap.add_argument("-f", "--force", action="store_true",
                    help="attempt to delete without confirmation or warning due to permission or file existence (override -i)")
    ap.add_argument("-v", "--verbose", action="store_true", help="explain what is being done")
    ap.add_argument("paths", type=Path, nargs="+", help="files or directories to delete")

    ns = ap.parse_args(args)

    try:
        for path in ns.paths:
            rm(path, ns)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
