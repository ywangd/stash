# -*- coding: utf-8 -*-
""" Summarize disk usage of the set of FILEs, recursively for directories.
"""
from __future__ import print_function
import os
import sys
from argparse import ArgumentParser
from fnmatch import fnmatch


def is_excluded(path, pattern):
    if pattern:
        while path != '':
            prefix, tail = os.path.split(path)
            if fnmatch(tail, pattern):
                return True
            else:
                path = prefix
        return False
    else:
        return False


def main(args):
    ap = ArgumentParser(
        description='Summarize disk usage of the set of FILEs, recursively for directories.'
    )
    ap.add_argument('-s', '--summarize', action='store_true',
                    help='display only a total for each argument')
    ap.add_argument('--exclude', dest='exclude_pattern',
                    metavar='PATTERN',
                    help='exclude files that match PATTERN')
    ap.add_argument('FILEs', nargs='*', default=['.'],
                    help='files to summarize (default to current working directory')

    ns = ap.parse_args(args)

    exclude_pattern = ns.exclude_pattern if ns.exclude_pattern else None

    sizeof_fmt = globals()['_stash'].libcore.sizeof_fmt

    for path in ns.FILEs:

        path_base = os.path.dirname(path)

        # Use relative path because of the following facts:
        # du A/B --exclude="B"  -> no output
        # du A/B --exclude="A"  -> normal output
        if is_excluded(os.path.relpath(path, path_base), exclude_pattern):
            continue

        if os.path.isdir(path):
            dirs_dict = {}
            # We need to walk the tree from the bottom up so that a directory can have easy
            # access to the size of its subdirectories.
            for root, dirs, files in os.walk(path, topdown=False):
                # This is to make sure the directory is not exclude from its ancestor
                if is_excluded(os.path.relpath(root, path_base), exclude_pattern):
                    continue

                # Loop through every non directory file in this directory and sum their sizes
                size = sum(os.path.getsize(os.path.join(root, name))
                           for name in files if not is_excluded(name, exclude_pattern))

                # Look at all of the subdirectories and add up their sizes from the `dirs_dict`
                subdir_size = sum(dirs_dict[os.path.join(root, d)]
                                  for d in dirs if not is_excluded(d, exclude_pattern))

                # store the size of this directory (plus subdirectories) in a dict so we
                # can access it later
                my_size = dirs_dict[root] = size + subdir_size

                if ns.summarize and root != path:
                    continue

                print('%-8s %s' % (sizeof_fmt(my_size), root))
        else:
            print('%-8s %s' % (sizeof_fmt(os.path.getsize(path)), path))


if __name__ == '__main__':
    main(sys.argv[1:])