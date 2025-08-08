#!/usr/bin/env python

import sys
import os
import json
import argparse
import pytz
import console

from datetime import datetime
from difflib import unified_diff


# _____________________________________________________
def argue():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("lhs")
    parser.add_argument("rhs")
    args = parser.parse_args()
    if args.verbose:
        json.dump(vars(args), sys.stderr, indent=4)
    return args


# _____________________________________________________
def sn(x):
    return "%s\n" % x


# _____________________________________________________
def modified(f):
    lmt = os.path.getmtime(f)
    est = pytz.timezone("Australia/Sydney")
    gmt = pytz.timezone("GMT")
    tzf = "%Y-%m-%d %H:%M:%S"
    gdt = datetime.utcfromtimestamp(lmt)
    gdt = gmt.localize(gdt)
    adt = est.normalize(gdt.astimezone(est))
    return adt.strftime(tzf)


# _____________________________________________________
def diff(lhs, rhs):
    if not os.path.isfile(lhs):
        sys.stderr.write("%s not a file\n" % lhs)
        sys.exit(1)
    if os.path.isdir(rhs):
        rhs = "%s/%s" % (rhs, os.path.basename(lhs))
    if not os.path.isfile(rhs):
        sys.stderr.write("%s not a file\n" % rhs)
        sys.exit(1)

    flhs = open(lhs).readlines()
    frhs = open(rhs).readlines()

    diffs = unified_diff(
        flhs,
        frhs,
        fromfile=lhs,
        tofile=rhs,
        fromfiledate=modified(lhs),
        tofiledate=modified(rhs),
    )
    for line in diffs:
        if line.startswith("+"):
            console.set_color(0, 1, 0)
        if line.startswith("-"):
            console.set_color(0, 0, 1)
            sys.stdout.write(line)
        console.set_color(1, 1, 1)
    return


# _____________________________________________________
def main():
    console.clear()
    args = argue()
    diff(args.lhs.rstrip("/"), args.rhs.rstrip("/"))
    return


# _____________________________________________________
if __name__ == "__main__":
    main()
