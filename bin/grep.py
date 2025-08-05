# -*- coding: utf-8 -*-
"""Search a regular expression pattern in one or more files"""

from __future__ import print_function

import argparse
import collections
import fileinput
import os
import re
import sys


def main(args):
    global _stash
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern", help="the pattern to match")
    ap.add_argument("files", nargs="*", help="files to be searched")
    ap.add_argument(
        "-i", "--ignore-case", action="store_true", help="ignore case while searching"
    )
    ap.add_argument(
        "-v", "--invert", action="store_true", help="invert the search result"
    )
    ap.add_argument(
        "-c",
        "--count",
        action="store_true",
        help="count the search results instead of normal output",
    )
    ns = ap.parse_args(args)

    flags = 0
    if ns.ignore_case:
        flags |= re.IGNORECASE

    pattern = re.compile(ns.pattern, flags=flags)

    # Do not try to grep directories
    files = [f for f in ns.files if not os.path.isdir(f)]

    fileinput.close()  # in case it is not closed
    try:
        counts = collections.defaultdict(int)
        for line in fileinput.input(files, openhook=fileinput.hook_encoded("utf-8")):
            if bool(pattern.search(line)) != ns.invert:
                if ns.count:
                    counts[fileinput.filename()] += 1
                else:
                    if ns.invert:  # optimize: if ns.invert, then no match, so no highlight color needed
                        newline = line
                    else:
                        newline = re.sub(
                            pattern, lambda m: _stash.text_color(m.group(), "red"), line
                        )
                    if fileinput.isstdin():
                        fmt = "{lineno}: {line}"
                    else:
                        fmt = "{filename}: {lineno}: {line}"

                    print(
                        fmt.format(
                            filename=fileinput.filename(),
                            lineno=fileinput.filelineno(),
                            line=newline.rstrip(),
                        )
                    )

        if ns.count:
            for filename, count in counts.items():
                fmt = "{count:6} {filename}"
                print(fmt.format(filename=filename, count=count))

    except Exception as err:
        print("grep: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
    finally:
        fileinput.close()


if __name__ == "__main__":
    main(sys.argv[1:])
