# -*- coding: utf-8 -*-
"""Show information about this StaSh installation."""

from __future__ import print_function

import os
import io
import sys
import time
import platform
import plistlib

_stash = globals()["_stash"]

try:
    collapseuser = _stash.libcore.collapseuser
except AttributeError:
    collapseuser = None

if not collapseuser:

    def collapseuser(p):
        return p


IN_PYTHONISTA = sys.executable.find("Pythonista") >= 0


# Following functions for getting Pythonista and iOS version information are adapted from
# https://github.com/cclauss/Ten-lines-or-less/blob/master/pythonista_version.py
def pythonista_version():  # 2.0.1 (201000)
    try:
        path = os.path.abspath(os.path.join(sys.executable, "..", "Info.plist"))
        with io.open(path, "rb") as fin:
            plist = plistlib.load(fin)
        return "{CFBundleShortVersionString} ({CFBundleVersion})".format(**plist)
    except Exception as e:
        return "UNKNOWN ({e})".format(e=repr(e))


def ios_version():  # 9.2 (64-bit iPad5,4)
    try:
        ios_ver, _, machine_model = platform.mac_ver()
    except Exception as e:
        return "UNKNOWN ({e})".format(e=repr(e))
    else:
        bit = platform.architecture()[0].rstrip("bit") + "-bit"
        return "{} ({} {})".format(ios_ver, bit, machine_model)


def print_stash_info():
    """
    Print general StaSh information.
    """
    STASH_ROOT = os.environ["STASH_ROOT"]
    print(
        _stash.text_style(
            "StaSh v%s" % globals()["_stash"].__version__,
            {"color": "blue", "traits": ["bold"]},
        )
    )
    print(
        "{} {} ({})".format(
            _stash.text_bold("Python"),
            os.environ["STASH_PY_VERSION"],
            platform.python_implementation(),
        )
    )
    print("{} {}".format(_stash.text_bold("UI"), _stash.ui.__module__))
    print("{}: {}".format(_stash.text_bold("root"), collapseuser(STASH_ROOT)))
    _stat = os.stat(os.path.join(STASH_ROOT, "core.py"))
    last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime))
    print("{}: {}".format(_stash.text_bold("core.py"), last_modified))
    print(
        "{}: {}".format(
            _stash.text_bold("SELFUPDATE_TARGET"), os.environ["SELFUPDATE_TARGET"]
        )
    )


def print_pythonista_info():
    """
    Print pythonista related informations.
    """
    print("{} {}".format(_stash.text_bold("Pythonista"), pythonista_version()))
    print("{} {}".format(_stash.text_bold("iOS"), ios_version()))


def print_paths():
    """
    Print path related informations
    """
    print(_stash.text_bold("BIN_PATH:"))
    for p in os.environ["BIN_PATH"].split(":"):
        print("  {}".format(collapseuser(p)))
    print(_stash.text_bold("PYTHONPATH:"))
    for p in os.environ["PYTHONPATH"].split(":"):
        print("  {}".format(collapseuser(p)))


def print_machine_info():
    """
    Print information about the current machine.
    """
    if IN_PYTHONISTA:
        print_pythonista_info()
    print("{} {}".format(_stash.text_bold("Platform"), platform.platform()))


def print_libs():
    """
    Print loaded libs.
    """
    print(_stash.text_bold("Loaded libraries:"))
    for an in dir(_stash):
        if an.startswith("lib"):
            print("  {}".format(an))


def main():
    print_stash_info()
    print_machine_info()
    print_paths()
    print_libs()


if __name__ == "__main__":
    main()
