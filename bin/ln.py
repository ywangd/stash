#!/usr/bin/env python

import sys, os, re, json, argparse, time, pytz
import console
from datetime import datetime, timedelta
from difflib import unified_diff, ndiff


def argue():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-s", "--symbolic", action="store_true")
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("lhs")
    parser.add_argument("rhs")
    args = parser.parse_args()
    if args.verbose:
        json.dump(vars(args), sys.stderr, indent=4)
    return args


def ln(lhs, rhs, symbolic=False):
    if not os.path.exists(lhs):
        sys.stderr.write("%s not found\n" % lhs)
        sys.exit(1)
    if os.path.isdir(rhs):
        rhs = "%s/%s" % (rhs, os.path.basename(lhs))
    if os.path.isfile(rhs):
        sys.stderr.write("%s already exists\n" % rhs)
        sys.exit(1)
    if os.path.islink(rhs):
        sys.stderr.write("%s already linked\n" % rhs)
        sys.exit(1)

    if symbolic:
        os.symlink(lhs, rhs)
    else:
        os.link(lhs, rhs)
    return


def main():
    console.clear()
    args = argue()
    ln(args.lhs, args.rhs, args.symbolic)
    return


if __name__ == "__main__":
    main()
