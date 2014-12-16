#!/usr/bin/env python
########################################################################.......

"""Open file in the Pythonista editor.
"""

from __future__ import print_function

import argparse
import console
import editor
import os
import sys

def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("file", action="store", help="file to open")
    ns = p.parse_args(args)
    
    editor.open_file(os.path.relpath(ns.file, os.path.expanduser("~/Documents")))
    console.hide_output()
    
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])
