# -*- coding: utf-8 -*-
"""Print standard input or files, omitting repeated lines"""

import argparse
import fileinput
import sys
from pathlib import Path


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", type=Path, nargs="*", help="files to unique (must be sorted first)")
    ns = ap.parse_args(args)

    def _print(lines):
        if lines is not None:
            print("".join(lines))

    try:
        prev_line = None
        lines = None

        with fileinput.input(files=ns.files, openhook=fileinput.hook_encoded("utf-8")) as fin:
            for line in fin:
                if fileinput.isfirstline():
                    _print(lines)
                    lines = []
                    prev_line = None
                if prev_line is None or line != prev_line:
                    lines.append(line)
                prev_line = line

            _print(lines)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("uniq: error: %s" % str(e), file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
