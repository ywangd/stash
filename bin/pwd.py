#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Print the current working directory."""

import argparse
import os
import sys

# We'll assume a standard Python environment without the custom _stash module
# to make the script more portable.
try:
    _stash = globals()["_stash"]
    collapseuser = _stash.libcore.collapseuser
except (KeyError, AttributeError):
    collapseuser = None


def main(args):
    """
    The main function to parse arguments and print the working directory.
    """
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-b", "--basename", action="store_true", help="show basename only")
    ap.add_argument("-f", "--fullname", action="store_true", help="show full path")
    ns = ap.parse_args(args)

    try:
        if ns.fullname:
            print(os.getcwd())
        elif ns.basename:
            print(os.path.basename(os.getcwd()))
        else:
            # The default behavior should be to print the full path,
            # or the collapsed path if available.
            current_path = os.getcwd()
            if collapseuser is not None:
                print(collapseuser(current_path))
            else:
                print(current_path)

        # The script should only exit with a 0 status on success
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        # The script should exit with a non-zero status on error
        sys.exit(1)
    except Exception as err:
        print("pwd: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        # The script should exit with a non-zero status on error
        sys.exit(1)


if __name__ == "__main__":
    # We call main with sys.argv[1:] to exclude the script name
    main(sys.argv[1:])
