# -*- coding: utf-8 -*-
"""Find files in specified paths"""

from __future__ import print_function

import os
import sys
import argparse
import time
import fnmatch
from functools import partial


class FilePredicate(object):
    def __init__(self):
        self.funclist = []

    def add_filter(self, func):
        self.funclist.append(func)

    def run(self, paths):
        names = []
        for pth in paths:
            for root, dirs, files in os.walk(os.path.normpath(pth)):
                for func in self.funclist:
                    root, dirs, files = func(root, dirs, files, pth)
                    if root is None:
                        break
                if root is not None:
                    names.extend(os.path.join(root, f) for f in files)
                    names.extend(os.path.join(root, d + os.path.sep) for d in dirs)

        return names


def filter_depth_and_type(mindepth, maxdepth, ftype, root, dirs, files, pth):
    root_rel = os.path.relpath(root, pth)
    if root_rel == ".":
        level = 0
    else:
        level = len(root_rel.split(os.path.sep))

    if level > maxdepth:
        return None, None, None

    elif not (mindepth <= level <= maxdepth):
        files = []

    if ftype == "f":
        if not dirs and not files:
            return None, None, None
        else:
            if level == maxdepth:
                dirs = []
            else:
                return root, dirs, files
    elif ftype == "d":
        files = []

    return root, dirs, files


def filter_name(pattern, root, dirs, files, pth):
    files = fnmatch.filter(files, pattern)
    dirs = fnmatch.filter(dirs, pattern)
    if not files and not dirs and not fnmatch.fnmatch(root, pattern):
        return None, None, None
    return root, dirs, files


def filter_mtime(oldest_time, newest_time, root, dirs, files, pth):
    fnames = []
    for f in files:
        st_mtime = os.stat(os.path.join(root, f)).st_mtime
        if newest_time > st_mtime > oldest_time:
            fnames.append(f)

    dnames = []
    for d in dirs:
        st_mtime = os.stat(os.path.join(root, d)).st_mtime
        if newest_time > st_mtime > oldest_time:
            dnames.append(d)

    if not fnames and not dnames:
        st_mtime = os.stat(root).st_mtime
        if not (newest_time > st_mtime > oldest_time):
            return None, None, None

    return root, dnames, fnames


def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "paths", nargs="+", help="specify a file hierarchy for find to traverse"
    )
    ap.add_argument(
        "-n",
        "-name",
        "--name",
        dest="pattern",
        nargs="?",
        default="*",
        help="pattern to match file names",
    )
    ap.add_argument(
        "-t",
        "-type",
        "--type",
        nargs="?",
        default="f",
        choices=("a", "f", "d"),
        help="specify the file type to match",
    )
    ap.add_argument(
        "-d",
        "-mtime",
        "--mtime",
        metavar="n",
        nargs="?",
        help="specify modification time range",
    )

    ap.add_argument(
        "-mindepth",
        "--mindepth",
        metavar="n",
        nargs="?",
        default=0,
        type=int,
        help="descend at most n directory levels below command line arguments",
    )
    ap.add_argument(
        "-maxdepth",
        "--maxdepth",
        metavar="n",
        nargs="?",
        default=sys.maxsize,
        type=int,
        help="descend at most n directory levels below command line arguments",
    )
    ns = ap.parse_args(args)

    file_predicate = FilePredicate()

    file_predicate.add_filter(
        partial(filter_depth_and_type, ns.mindepth, ns.maxdepth, ns.type)
    )

    file_predicate.add_filter(partial(filter_name, ns.pattern))

    if ns.mtime:
        oldest_time = 0
        tnow = newest_time = time.time()
        if ns.mtime.startswith("-"):
            ndays = int(ns.mtime[1:])
            oldest_time = tnow - ndays * 86400.0
        elif ns.mtime.startswith("+"):
            ndays = int(ns.mtime[1:])
            newest_time = tnow - (ndays + 1) * 86400.0
        else:
            ndays = int(ns.mtime)
            oldest_time = tnow - (ndays + 1) * 86400.0
            newest_time = tnow - ndays * 86400.0
        file_predicate.add_filter(partial(filter_mtime, oldest_time, newest_time))

    names = file_predicate.run(ns.paths)

    print("\n".join(names))


if __name__ == "__main__":
    main(sys.argv[1:])
