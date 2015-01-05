#!/usr/bin/env python
########################################################################.......

"""Open file in Quick Look.
"""

from __future__ import print_function

import argparse
import console
import sys
import ui


class ConsoleQuicklook(object):

    def __init__(self, args):
        p = argparse.ArgumentParser(description=__doc__)
        p.add_argument("file", action="store", help="file to open")
        ns = p.parse_args(args)
        self.filename = ns.file

    @ui.in_background
    def preamble(self):
        print('WARNING: Do not switch window or Pythonista may freeze')
        print('Opening %s ...' % self.filename)

    @ui.in_background
    def _quicklook(self):
        console.quicklook(self.filename)

    def quicklook(self):
        self.preamble()
        ui.delay(self._quicklook, 1)


if __name__ == "__main__":
    ConsoleQuicklook(sys.argv[1:]).quicklook()

