# -*- coding: utf-8 -*-
"""subprocess tests."""

from __future__ import print_function
import subprocess

_stash = globals()["_stash"]
text = _stash.text_color

# exit test
print(text("starting exit test...", "yellow"))
try:
    subprocess.check_call("exit 0")
    print(text("	0 OK", "green"))
except subprocess.CalledProcessError:
    print(text("	0 ERROR", "red"))
try:
    subprocess.check_call("exit 1")
    print(text("	1 ERROR", "red"))
except subprocess.CalledProcessError:
    print(text("	1 OK", "green"))

# parent I/O
print(text("\nstarting parent I/O test...", "yellow"))
print("		please check for I/O")
subprocess.call("man readme")

# output test
print(text("\nstarting check_output test...", "yellow"))
string = "Test"
try:
    output = subprocess.check_output("echo " + string)
    if output.endswith("\n") and (not string.endswith("\n")):
        output = output[:-1]
    if output != string:
        print(text("	0 ERROR output does not match!\n	" + output, "red"))
    else:
        print(text("	0 OK", "green"))
except subprocess.CalledProcessError:
    print(text("	0 ERROR", "red"))
try:
    output = subprocess.check_output("gci wasd")
    print(text("	1 ERROR", "red"))
except subprocess.CalledProcessError:
    print(text("	1 OK", "green"))
