# -*- coding: utf-8 -*-
"""Copy one or more files to the system clipboard"""

from __future__ import print_function

import argparse
import fileinput
import os
import sys


_stash = globals()["_stash"]


def main(args):
    """
    The main function.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="*", help="one or more files to be copied")
    ns = ap.parse_args(args)

    if not hasattr(_stash, "libdist"):
        print(_stash.text_color("Error: libdist not loaded.", "red"))
        sys.exit(1)

    fileinput.close()  # in case it is not closed
    try:
        _stash.libdist.clipboard_set(
            "".join(
                line
                for line in fileinput.input(
                    ns.file, openhook=fileinput.hook_encoded("utf-8")
                )
            )
        )
    except Exception as err:
        print(
            _stash.text_color(
                "pbcopy: {}: {!s}".format(type(err).__name__, err), "red"
            ),
            file=sys.stderr,
        )
        sys.exit(1)
    finally:
        fileinput.close()


if __name__ == "__main__":
    main(sys.argv[1:])
