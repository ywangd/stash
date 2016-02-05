# coding=utf-8
import os
import unittest

import stash

class RuntimeTests(unittest.TestCase):

    def setUp(self):
        self.stash = stash.StaSh()
        self.stash('cd $STASH_ROOT')
        self.stash('BIN_PATH=$STASH_ROOT/system/tests/data:$BIN_PATH')

    def tearDown(self):
        assert self.stash.runtime.child_thread is None, 'child thread is not cleared'
        assert len(self.stash.runtime.worker_registry) == 0, 'worker registry not empty'
        del self.stash

    def do_test(self, cmd, cmp_str, ensure_same_cwd=True, ensure_undefined=(), ensure_defined=()):

        saved_cwd = os.getcwd()
        self.stash('clear')
        self.stash(cmd)

        assert cmp_str == self.stash.main_screen.text, 'output not identical'

        if ensure_same_cwd:
            assert os.getcwd() == saved_cwd, 'cwd changed'

        for v in ensure_undefined:
            assert v not in self.stash.runtime.state.environ.keys(), '%s should be undefined' % v

        for v in ensure_defined:
            assert v in self.stash.runtime.state.environ.keys(), '%s should be defined' % v

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

