# -*- coding: utf-8 -*-
"""Copy a file or directory. Multiple source files may be specified if the destination is
an existing directory.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Sequence


def _home_relative_path(path: Path) -> Path:
    home2 = os.environ.get("HOME") or Path("~").expanduser() / "Documents"
    return path.relative_to(home2) if path.is_relative_to(home2) else path


def main(args: Sequence[str]) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", type=Path, nargs="+", help="one or more files or directories to be copied")
    ap.add_argument("dest", type=Path, help="destination file or folder")
    ns = ap.parse_args(args)

    # Check if all source paths exist
    for source_path in ns.source:
        if not source_path.exists():
            print(f"cp: {_home_relative_path(source_path)}: No such file or directory", file=sys.stderr)
            sys.exit(1)

    # Check the number of source files/directories.
    # If there's more than one source, the destination must be a directory.
    if len(ns.source) > 1 and not ns.dest.is_dir():
        print(f"cp: target '{_home_relative_path(ns.dest)}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Iterate through all source paths and copy them.
    for source_path in ns.source:
        try:
            if source_path.is_dir():
                # For directories, use shutil.copytree.
                # If the destination is an existing directory, we must specify the new path.
                dest_path = ns.dest / source_path.name if ns.dest.is_dir() else ns.dest
                shutil.copytree(source_path, dest_path)
            else:
                # For files, use shutil.copy.
                # This function handles destinations that are files or directories automatically.
                shutil.copy(source_path, ns.dest)
        except shutil.Error as err:
            # Handle shutil-specific errors (e.g., trying to copy a file onto itself)
            print(f"cp: {_home_relative_path(source_path)}: {err}", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            # Handle user interruption (Ctrl+C)
            print("\ncp: Operation interrupted by user.", file=sys.stderr)
            sys.exit(1)
        except Exception as err:
            # Handle other unexpected errors
            print(f"cp: {type(err).__name__}: {err}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
