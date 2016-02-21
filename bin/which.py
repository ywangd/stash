""" Locate a command script in BIN_PATH. No output if command is not found.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

import argparse


def main(command, fullname=False):
    rt = globals()['_stash'].runtime
    try:
        filename = rt.find_script_file(command)
        if not fullname:
            filename = _stash.libcore.collapseuser(filename)
        print(filename)
    except Exception:
        pass

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command', help='name of the command to be located')
    ap.add_argument('-f', '--fullname', action='store_true',
                    help='show full path')
    ns = ap.parse_args()
    main(ns.command, ns.fullname)