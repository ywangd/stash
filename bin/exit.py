#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Exit the current subshell, optionally with a specific status. If no
status is given, the default of 0 is used, indicating successful
execution with no errors.
"""

import argparse
import os
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("status", action="store", nargs="?", default=0,
                   type=int, help="status code")
    ns = p.parse_args(args)
    sys.exit(ns.status)

if __name__ == "__main__":
    main(sys.argv[1:])
