#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""List current environment variables and values."""

from __future__ import division, print_function, unicode_literals

import argparse
import os
import sys


def main(args):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "variables", action="store", nargs="*", help="variables to be printed"
    )
    ns = p.parse_args(args)

    if ns.variables:
        vardict = {k: v for k, v in os.environ.items() if k in ns.variables}
    else:
        vardict = os.environ

    vardict = {k: v for k, v in vardict.items() if k[0] not in "$@?!#*0123456789"}

    for k, v in vardict.items():
        print("{}={}".format(k, v))

    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])
