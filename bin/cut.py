""" Print selected parts of lines from each FILE to standard output.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import os
import sys
import argparse

_stash = globals()['_stash']

def construct_indices_from_list_spec(list_spec):
    # Note unlike python, cut's indices start from 1
    indices = []
    for fld in list_spec.split(','):
        if '-' in fld:
            sidx, eidx = fld.split('-')
            sidx = int(sidx) - 1
            eidx = int(eidx)  # -1 + 1 because base is 1 and eidx is inclusive
        else:
            sidx = int(fld) - 1
            eidx = sidx + 1

        indices.append((sidx, eidx))
    return indices


def main(args):
    ap = argparse.ArgumentParser()

    ap.add_argument('-d', '--delimiter',
                    nargs='?',
                    metavar='DELIM',
                    help='use DELIM instead of SPACE for field delimiter')
    ap.add_argument('-f', '--fields',
                    required=True,
                    metavar='LIST',
                    help='select only these fields')
    ap.add_argument('files', nargs='*', help='files to cut')
    ns = ap.parse_args(args)

    indices = construct_indices_from_list_spec(ns.fields)

    for infields in _stash.libcore.input_stream(ns.files):
        if infields[0] is None:
            _, filename, e = infields
            print('%s: %s' % (filename, repr(e)))
        else:
            line, filename, lineno = infields
            fields = line.split(ns.delimiter)
            if len(fields) == 1:
                print(fields[0])
            else:
                out = ' '.join((' '.join(fields[sidx:eidx]) for sidx, eidx in indices))
                print(out)

if __name__ == '__main__':
    main(sys.argv[1:])