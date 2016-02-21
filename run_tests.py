# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import argparse
import unittest

ap = argparse.ArgumentParser()
ap.add_argument('-v', '--verbose', action='store_true', help='be more chatty')
ap.add_argument('-p', '--pattern', default='test_*.py', help='the pattern to search test files')
ns = ap.parse_args()

testsuite = unittest.defaultTestLoader.discover('system', pattern=ns.pattern)
runner = unittest.TextTestRunner(verbosity=2 if ns.verbose else 1)

runner.run(testsuite)
