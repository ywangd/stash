# -*- coding: utf-8 -*-
"""Writes the contents of the system clipboard to a file."""

from __future__ import print_function

import argparse
import os
import sys
import io


_stash = globals()["_stash"]


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="the file to be pasted")
    ns = ap.parse_args(args)

    status = 0

    if not hasattr(_stash, "libdist"):
        print(_stash.text_color("Error: libdist not loaded.", "red"))
        sys.exit(1)

    content = _stash.libdist.clipboard_get()
    if ns.file:
        if os.path.exists(ns.file):
            print(
                _stash.text_color("pbpaste: {}: file exists".format(ns.file), "red"),
                file=sys.stderr,
            )
            status = 1
        else:
            try:
                if isinstance(content, (bytes, bytearray)):
                    with io.open(ns.file, "wb") as f:
                        f.write(content)
                else:
                    with io.open(ns.file, "w", encoding="utf-8") as f:
                        f.write(content)
            except Exception as err:
                print(
                    "pbpaste: {}: {!s}".format(type(err).__name__, err), file=sys.stderr
                )
                status = 1
    else:
        print(content, end="")

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
