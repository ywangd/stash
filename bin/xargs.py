""" Construct argument list(s) and execute utility
"""

import os
import sys
import argparse

_stash = globals()['_stash']

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('args_to_xargs', nargs='*', help='arguments to xargs')
    ns = ap.parse_args(args)
    args_to_xargs = ns.args_to_xargs

    if args_to_xargs:
        cmd = args_to_xargs.pop(0)
    else:
        cmd = 'echo'

    for line in sys.stdin.readlines():
        _stash('%s %s' % (cmd, ' '.join(args_to_xargs + [line.strip()])))


if __name__ == "__main__":
    main(sys.argv[1:])