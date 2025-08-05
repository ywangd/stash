# -*- coding: utf-8 -*-
from __future__ import print_function

s = globals()["_stash"]

# following statements should be correlated
s("echo AA is $AA")
s("AA=Hello")
# AA should now be set
s("echo AA is $AA")
s("pwd -b")
s("cd bin")
# cwd should now be changed
s("pwd -b")
s("cd ..")

print()
# following two scripts should not interfere each other
s("test05_1.sh")

s("test05_2.sh")
