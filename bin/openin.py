#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Open file in an external app.
"""

from __future__ import print_function

import argparse
import console
import sys
import ui


class ConsoleOpenin(object):

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
    def _open_in(self):
        console.open_in(self.filename)

    def open_in(self):
        self.preamble()
        ui.delay(self._open_in, 1)


if __name__ == "__main__":
    ConsoleOpenin(sys.argv[1:]).open_in()
