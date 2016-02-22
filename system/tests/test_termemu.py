# coding=utf-8
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import unittest

from stash import stash

class TermemuTests(unittest.TestCase):

    def setUp(self):
        self.stash = stash.StaSh()
        self.stash('cd $STASH_ROOT')
        self.stash('BIN_PATH=$STASH_ROOT/system/tests/data:$BIN_PATH')
        self.stash('clear')

    def tearDown(self):
        assert self.stash.runtime.child_thread is None, 'child thread is not cleared'
        assert len(self.stash.runtime.worker_registry) == 0, 'worker registry not empty'
        del self.stash

    def test_201(self):
        self.stash('test_201.py')
        cmp_str = """[stash]$ The first line
[stash]$ rown fox jumps over the lazy dog"""
        assert self.stash.main_screen.text == cmp_str, 'output not identical'

    def test_202(self):
        self.stash('test_202.py')
        cmp_str = """[stash]$ The first line
[stash]$ """
        assert self.stash.main_screen.text == cmp_str, 'output not identical'

    def test_203(self):
        self.stash('test_203.py')
        cmp_str = """[stash]$ The first line
[stash]$                                 """
        assert self.stash.main_screen.text == cmp_str

    def test_204(self):
        self.stash('test_204.py')
        cmp_str = """[stash]$ The first line
A quick brown fox jumps over the lazy do[stash]$ """
        assert self.stash.main_screen.text == cmp_str

if __name__ == '__main__':
    unittest.main()