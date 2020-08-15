# coding=utf-8

from stash.tests.stashtest import StashTestCase


class RuntimeTests(StashTestCase):

    setup_commands = ['BIN_PATH=$STASH_ROOT/tests/system/data:$BIN_PATH']

    def test_03(self):
        cmp_str = r"""[stash]$ x y
A is{0}
A is 8
bin
[stash]$ """.format(' ')
        self.do_test('test03.sh x y', cmp_str, ensure_undefined=('A', ))

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
paste=pbpaste
unmount=umount

AA is{0}
copy=pbcopy
env=printenv
help=man
la=ls -a
ll=ls -la
paste=pbpaste
unmount=umount


--- source the file ---
From tobesourced AA is sourced
copy=pbcopy
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
paste=pbpaste
unmount=umount

AA is sourced
copy=pbcopy
env=printenv
help=man
l1=ls -1
la=ls -a
ll=ls -la
paste=pbpaste
unmount=umount

[stash]$ """.format(' ')
        self.do_test('test06.sh', cmp_str, ensure_undefined=('A', ))

    def test_07(self):
        cmp_str = r"""[stash]$ A is 999
A is{0}
[stash]$ """.format(" ")
        self.do_test('test07.sh', cmp_str, ensure_undefined=('A', ))

    def test_08(self):
        cmp_str = r"""[stash]$ A is{0}
[stash]$ """.format(" ")
        self.do_test('test08.sh', cmp_str, ensure_undefined=('A', ))

    def test_09(self):
        cmp_str = r"""[stash]$ A is{0}
[stash]$ """.format(' ')
        self.do_test('test09.sh', cmp_str, ensure_undefined=('A', ))

    def test_10(self):
        cmp_str = r"""[stash]$ 1: #!/bin/bash
[stash]$ """
        self.do_test('test10.sh', cmp_str)

    def test_11(self):
        cmp_str = r"""[stash]$ A is 42
[stash]$ """
        self.do_test('test11.sh', cmp_str, ensure_undefined=('A', ))

    def test_12(self):
        """
        Directory changes in script via callable interface should not
        affect parent shell but is persistent for any following calls
        from the same parent shell.
        """
        cmp_str = r"""[stash]$ parent script stash
parent script stash
from child script 2 bin
parent script stash
[stash]$ """
        self.do_test('test_12.py', cmp_str)
