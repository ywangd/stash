"""
Testings on both PC or iOS
"""

import os
import sys
import unittest

import stash


class StashTests(unittest.TestCase):

    def setUp(self):
        self.stash = stash.StaSh()
        self.stash('cd $STASH_ROOT')
        self.stash('BIN_PATH=$STASH_ROOT/tests:$BIN_PATH')
        self.complete = self.stash.completer.complete

    def tearDown(self):
        assert len(self.stash.runtime.worker_stack) == 0, 'Worker stack is not clean'
        assert len(self.stash.runtime.state_stack) == 0, 'State stack is not clean'
        del self.stash

    def do_test(self, cmd, cmp_str, ensure_same_cwd=True, ensure_undefined=(), ensure_defined=()):

        saved_cwd = os.getcwd()
        self.stash('clear')
        self.stash(cmd)
    
        assert cmp_str == self.stash.term.out_buf, 'output not identical'
    
        if ensure_same_cwd:
            assert os.getcwd() == saved_cwd, 'cwd changed'
    
        for v in ensure_undefined:
            assert v not in self.stash.runtime.envars.keys(), '%self.stash should be undefined' % v
    
        for v in ensure_defined:
            assert v in self.stash.runtime.envars.keys(), '%self.stash should be defined' % v

    def test_03(self):
        cmp_str = r"""[stash]$ x y
A is{0}
A is 8
bin
[stash]$ """.format(' ')
        self.do_test('test03.sh x y', cmp_str, ensure_undefined=('A',))

    def test_05(self):
        cmp_str = r"""[stash]$ AA is{0}
AA is Hello
stash
bin

1
B is{0}
B is 89
bin
2
B is{0}
stash
[stash]$ """.format(' ')
        self.do_test('test05.py', cmp_str, ensure_undefined=('AA', 'B'))

    def test_06(self):
        cmp_str = r"""[stash]$ AA is{0}
--- direct execution without sourcing ---
From tobesourced AA is sourced
copy=pbcopy
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."
paste=pbpaste

AA is{0}
copy=pbcopy
env=printenv
help=man
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."
paste=pbpaste


--- source the file ---
From tobesourced AA is sourced
copy=pbcopy
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."
paste=pbpaste

AA is sourced
copy=pbcopy
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."
paste=pbpaste

[stash]$ """.format(' ')
        self.do_test('test06.sh', cmp_str, ensure_undefined=('A',))


    def test_07(self):
        cmp_str = r"""[stash]$ A is 999
A is{0}
[stash]$ """.format(" ")
        self.do_test('test07.sh', cmp_str, ensure_undefined=('A',))

    def test_08(self):
        cmp_str = r"""[stash]$ A is{0}
[stash]$ """.format(" ")
        self.do_test('test08.sh', cmp_str, ensure_undefined=('A',))

    def test_09(self):
        cmp_str = r"""[stash]$ A is{0}
[stash]$ """.format(" ")
        self.do_test('test09.sh', cmp_str, ensure_undefined=('A',))

    def test_10(self):
        cmp_str = r"""[stash]$ 1: #!/bin/bash
[stash]$ """
        self.do_test('test10.sh', cmp_str)

    def test_11(self):
        cmp_str = r"""[stash]$ A is 42
[stash]$ """
        self.do_test('test11.sh', cmp_str, ensure_undefined=('A',))

    def test_completion_01(self):
        newline, all_names, cursor_at = self.complete('pw')
        assert newline == 'pwd.py '

    def test_completion_02(self):
        newline, all_names, cursor_at = self.complete('pws', cursor_at=2)
        assert newline == 'pwd.py s'
        assert cursor_at == 7

    def test_completion_03(self):
        newline, all_names, cursor_at = self.complete('ls s', cursor_at=3)
        assert cursor_at == 3
        assert newline == 'ls s'
        assert 'README.md' in all_names
        assert 'source.py' not in all_names

    def test_completion_04(self):
        newline, all_names, cursor_at = self.complete('')
        assert newline == ''
        assert cursor_at == 0
        assert 'source.py' in all_names
        assert 'README.md' not in all_names

    def test_completion_05(self):
        newline, all_names, cursor_at = self.complete('ls README.md ')
        assert newline == 'ls README.md '
        assert cursor_at == 13
        assert 'CHANGES.md' in all_names
        assert 'source.py' not in all_names

    def test_completion_06(self):
        newline, all_names, cursor_at = self.complete('git ')
        assert newline == 'git '
        assert cursor_at == 4
        assert 'branch' in all_names
        assert 'clone' in all_names
        assert 'README.md' not in all_names

    def test_completion_07(self):
        newline, all_names, cursor_at = self.complete('ls -')
        assert newline == 'ls -'
        assert '--all' in all_names
        assert 'README.md' not in all_names

    def test_completion_08(self):
        newline, all_names, cursor_at = self.complete('git brREA', cursor_at=6)
        assert newline == 'git branch REA'
        assert cursor_at == 11

    def test_completion_09(self):
        newline, all_names, cursor_at = self.complete('$STASH_')
        assert newline == '$STASH_ROOT '

    def test_completion_10(self):
        newline, all_names, cursor_at = self.complete('$STASH_ROOT/bi')
        assert newline == '$STASH_ROOT/bin/'

    def test_completion_11(self):
        newline, all_names, cursor_at = self.complete('ls $STASH_ROOT/bi')
        assert newline == 'ls $STASH_ROOT/bin/'

    def test_completion_12(self):
        newline, all_names, cursor_at = self.complete('ls $STASH_ROOT/bin/ls.')
        assert newline == 'ls $STASH_ROOT/bin/ls.py '


if __name__ == '__main__':
    unittest.main()
