""" Locate a command script in BIN_PATH. No output if command is not found.
"""

import argparse


def main(command, fullname=False):
    rt = globals()['_stash'].runtime
    try:
        filename = rt.find_script_file(command) or _stash.libcore.collapseuser(filename)
        print filename
    except Exception:
        pass

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command', help='name of the command to be located')
    ap.add_argument('-f', '--fullname', action='store_true',
                    help='show full path')
    ns = ap.parse_args()
    main(ns.command, ns.fullname)
