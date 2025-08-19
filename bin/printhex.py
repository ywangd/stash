#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Print the given files' content and hexadecimal byte values."""

import argparse
import sys

INVISIBLE = list(range(0x20)) + [0x81, 0x8D, 0x8F, 0x90, 0x9D]


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "file", action="store", nargs="+", help="one or more files to be printed"
    )
    ns = p.parse_args(args)

    status = 0

    for filename in ns.file:
        try:
            with open(filename, "rb") as f:
                i = 0
                chunk = f.read(16)
                while chunk:
                    # Decoding as Latin-1 to get a visual representation for most
                    # bytes that would otherwise be non-printable.
                    str_chunk = "".join(
                        "_" if c in INVISIBLE else chr(c) for c in chunk
                    )
                    hex_chunk = " ".join("{:0>2X}".format(c) for c in chunk)
                    print("0x{:>08X} | {:<48} | {:<16}".format(i, hex_chunk, str_chunk))
                    i += 16
                    chunk = f.read(16)

        except Exception as err:
            print("printhex: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
            status = 1

    sys.exit(status)


if __name__ == "__main__":
    main(sys.argv[1:])
