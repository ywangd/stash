# -*- coding: utf-8 -*-
"""Construct argument list(s) and execute utility"""

import argparse
import sys

_stash = globals()["_stash"]


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "-n",
        nargs="?",
        metavar="number",
        type=int,
        help="maximum number of arguments taken from standard input for each invocation of utility",
    )

    ap.add_argument("-I", dest="replstr", nargs="?", help="replacement string")

    ap.add_argument("utility", nargs="?", default="echo", help="utility to invoke")

    ap.add_argument(
        "args_to_pass",
        metavar="arguments",
        nargs=argparse.REMAINDER,
        help="arguments to the utility",
    )

    ns = ap.parse_args(args)

    try:
        lines = [line.strip() for line in sys.stdin.readlines()]
        n = ns.n if ns.n else len(lines)
        if ns.replstr:
            n = 1

        while lines:
            rest = " ".join(lines[:n])
            lines = lines[n:]
            args_to_pass = " ".join(ns.args_to_pass)

            if rest.strip():
                if ns.replstr:
                    args_to_pass = args_to_pass.replace(ns.replstr, rest)
                    rest = ""

                cmdline = "%s %s %s" % (ns.utility, args_to_pass, rest)

                _stash(cmdline)
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("xargs: error: %s" % str(e), file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
