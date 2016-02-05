# coding=utf-8
import unittest

import stash

class CompleterTests(unittest.TestCase):

    def setUp(self):
        self.stash = stash.StaSh()
        self.stash('cd $STASH_ROOT')
        self.complete = self.stash.completer.complete

    def tearDown(self):
        del self.stash

    def test_completion_01(self):
        newline, possibilities = self.complete('pw')
        assert newline == 'pwd.py '

    def test_completion_03(self):
        newline, possibilities = self.complete('ls ')
        assert newline == 'ls '
        assert 'README.md' in possibilities
        assert 'source.py' not in possibilities

    def test_completion_04(self):
        newline, possibilities = self.complete('')
        assert newline == ''
        assert 'source.py' in possibilities
        assert 'README.md' not in possibilities

    def test_completion_05(self):
        newline, possibilities = self.complete('ls README.md ')
        assert newline == 'ls README.md '
        assert 'CHANGES.md' in possibilities
        assert 'source.py' not in possibilities

    def test_completion_06(self):
        newline, possibilities = self.complete('git ')
        assert newline == 'git '
        assert 'branch' in possibilities
        assert 'clone' in possibilities
        assert 'README.md' not in possibilities

    def test_completion_07(self):
        newline, possibilities = self.complete('ls -')
        assert newline == 'ls -'
        assert '--all' in possibilities
        assert 'README.md' not in possibilities

    def test_completion_08(self):
        newline, possibilities = self.complete('git br')
        assert newline == 'git branch '

    def test_completion_09(self):
        newline, possibilities = self.complete('$STASH_')
        assert newline == '$STASH_ROOT '

    def test_completion_10(self):
        newline, possibilities = self.complete('$STASH_ROOT/bi')
        assert newline.replace('\\', '/') == '$STASH_ROOT/bin/'

    def test_completion_11(self):
        newline, possibilities = self.complete('ls $STASH_ROOT/bi')
        assert newline.replace('\\', '/') == 'ls $STASH_ROOT/bin/'

    def test_completion_12(self):
        newline, possibilities = self.complete('ls $STASH_ROOT/bin/ls.')
        assert newline.replace('\\', '/') == 'ls $STASH_ROOT/bin/ls.py '