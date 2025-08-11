#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Change the current working directory."""

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence


def main(args: Sequence[str]) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    HOME2_DEFAULT = os.environ.get("HOME2", Path("~").expanduser() / "Documents")
    p.add_argument(
        "dir",
        action="store",
        type=Path,
        nargs="?",
        default=HOME2_DEFAULT,
        help="the new working directory",
    )
    ns = p.parse_args(args)

    try:
        err = ""
        if not ns.dir.exists():
            err = f"cd: {ns.dir}: No such file or directory"
        elif not ns.dir.is_dir():
            err = f"cd: {ns.dir}: Not a directory"
        elif not os.access(ns.dir, os.R_OK):  # X_OK allows dir enter
            err = f"cd: {ns.dir}: Access denied"

        if err:
            print(err)
            sys.exit(1)
            return  # Add return to stop execution in the mocked environment

        os.chdir(ns.dir)
        sys.exit(0) # Moved to be inside the try block

    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print("cd: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
