# -*- coding: utf-8 -*-
"""Locate a command script in BIN_PATH. No output if command is not found."""

from __future__ import print_function


def main(command, fullname=False):
    global _stash
    rt = globals()["_stash"].runtime
    try:
        filename = rt.find_script_file(command)
        if not fullname:
            filename = _stash.libcore.collapseuser(filename)
        print(filename)
    except Exception:
        pass


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("command", help="name of the command to be located")
    ap.add_argument("-f", "--fullname", action="store_true", help="show full path")
    ns = ap.parse_args()
    main(ns.command, ns.fullname)
