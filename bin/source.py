"""
Read and execute commands from a shell script in the current environment.

usage: source.py [-h] file [args [args ...]]

positional arguments:
  file        file to be sourced
  args        arguments to the file being sourced

optional arguments:
  -h, --help  show this help message and exit
"""
from __future__ import print_function

import sys
from argparse import ArgumentParser


def main(args):
    ap = ArgumentParser(
        description="Read and execute commands from a shell script in the current environment")
    ap.add_argument('file', action="store", help='file to be sourced')
    ap.add_argument(
        'args',
        nargs='*',
        help='arguments to the file being sourced')
    ns = ap.parse_args(args)

    _stash = globals()['_stash']
    """:type : StaSh"""

    _, current_state = _stash.runtime.get_current_worker_and_state()

    # The special thing about source is it persists any environmental changes
    # in the sub-shell to the parent shell.
    try:
        with open(ns.file) as ins:
            _stash(ins.readlines(), persistent_level=1)

    except IOError as e:
        print('%s: %s' % (e.filename, e.strerror))
    except Exception as e:
        print('error: %s' % str(e))
    finally:
        pass


if __name__ == '__main__':
    main(sys.argv[1:])
