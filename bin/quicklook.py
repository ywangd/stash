#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Open file in Quick Look.
"""

from __future__ import print_function

import argparse
import console
import sys
import ui

from objc_util import on_main_thread


class ConsoleQuicklook(object):

    def __init__(self, args):
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("file", action="store", help="file to open")
        ns = p.parse_args(args)
        self.filename = ns.file

    @on_main_thread
    def quicklook(self):
        console.quicklook(self.filename)


if __name__ == "__main__":
    ConsoleQuicklook(sys.argv[1:]).quicklook()

