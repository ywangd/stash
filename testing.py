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
        cmp_str = r"""x y
A is{0}
A is 8
bin
""".format(' ')
        self.do_test('test03.sh x y', cmp_str, ensure_undefined=('A',))

    def test_05(self):
        cmp_str = r"""AA is{0}
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
""".format(' ')
        self.do_test('test05.py', cmp_str, ensure_undefined=('AA', 'B'))

    def test_06(self):
        cmp_str = r"""AA is{0}
--- direct execution without sourcing ---
From tobesourced AA is sourced
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."

AA is{0}
env=printenv
help=man
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."


--- source the file ---
From tobesourced AA is sourced
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."

AA is sourced
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
logout=echo "Use the close button in the upper right corner to exit StaSh."

""".format(' ')
        self.do_test('test06.sh', cmp_str, ensure_undefined=('A',))


    def test_07(self):
        cmp_str = r"""A is 999
A is{0}
""".format(" ")
        self.do_test('test07.sh', cmp_str, ensure_undefined=('A',))

    def test_08(self):
        cmp_str = r"""A is{0}
""".format(" ")
        self.do_test('test08.sh', cmp_str, ensure_undefined=('A',))

    def test_09(self):
        cmp_str = r"""A is{0}
""".format(" ")
        self.do_test('test09.sh', cmp_str, ensure_undefined=('A',))

    def test_10(self):
        cmp_str = r"""1: #!/bin/bash
"""
        self.do_test('test10.sh', cmp_str)

    def test_11(self):
        cmp_str = r"""A is 42
"""
        self.do_test('test11.sh', cmp_str, ensure_undefined=('A',))


if __name__ == '__main__':
    unittest.main()
