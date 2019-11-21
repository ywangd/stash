#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Open file in an external app.
"""

from __future__ import print_function

import argparse
import sys


_stash = globals()["_stash"]


class ConsoleOpenin(object):
    def __init__(self, args):
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("file", action="store", help="file to open")
        ns = p.parse_args(args)
        self.filename = ns.file

    def open_in(self):
        _stash.libdist.open_in(self.filename)


if __name__ == "__main__":
    ConsoleOpenin(sys.argv[1:]).open_in()
