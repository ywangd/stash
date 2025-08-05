# -*- coding: utf-8 -*-
"""utility StaSh testcase for common methids"""

import os
import sys
import unittest
import logging
import tempfile

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import requests

from stash import stash
from stash.system.shcommon import _STASH_ROOT, PY3


ON_TRAVIS = "TRAVIS" in os.environ


def network_is_available():
    """
    Check whether the network is available.
    :return: whether the network is available.
    :rtype: bool
    """
    # to be sure, test multiple sites in case one of them is offline
    test_sites = [
        "https://github.com/ywangd/stash/",  # main StaSh repo
        "https://forum.omz-software.com/",  # pythonista forums
        "https://python.org/",  # python website
    ]
    for url in test_sites:
        try:
            requests.get(url, timeout=5.0)
        except (requests.ConnectionError, requests.Timeout):
            # can not connect, retry.
            continue
        else:
            # successfully connected.
            return True
    return False


def requires_network(f):
    """
    Decorator for specifying that a test needs a network connection.
    If no network connection is available, skip test.
    :param f: test function
    :type f: callable
    :return: decorated function
    :rtype: callable
    """
    network_unavailable = not network_is_available()
    return unittest.skipIf(network_unavailable, "No network connection available.")(f)


def expected_failure_on_py3(f):
    """
    Decorator for specifying that a test will probably fail on py3.
    :param f: test function
    :type f: callable
    :return: decorated function
    :rtype: callable
    """
    if PY3:
        return unittest.expectedFailure(f)
    else:
        return f


class StashTestCase(unittest.TestCase):
    """A test case implementing utility methods for testing StaSh"""

    cwd = "$STASH_ROOT"
    setup_commands = []
    environment = {
        "STASH_ROOT": _STASH_ROOT,
        "TMP": tempfile.gettempdir(),
        "TMPDIR": tempfile.gettempdir(),
    }

    maxDiff = 4096  # max diff size

    def get_data_path(self):
        """return the data/ sibling path"""
        curpath = os.path.dirname(sys.modules[self.__module__].__file__)
        return os.path.abspath(os.path.join(curpath, "data"))

    def setUp(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stash = stash.StaSh()

        self.logger.debug("preparing environment...")
        for kn in self.environment:
            if kn not in os.environ:
                v = self.environment[kn]
                self.logger.debug("Setting $" + str(kn) + " to: " + repr(v))
                os.environ[kn] = v

        self.logger.debug("preparing sys.path...")
        libpath = os.path.abspath(os.path.join(_STASH_ROOT, "lib"))

        self.logger.debug("Enabling tracebacks...")
        if libpath not in sys.path:
            sys.path.append(libpath)
        self.stash("stashconf py_traceback 1")

        self.cwd = os.path.abspath(os.path.expandvars(self.cwd))
        self.logger.info("Target CWD is: " + str(self.cwd))
        self.stash("cd " + self.cwd, persistent_level=1)
        self.logger.debug("After cd, CWD is: " + os.getcwd())

        for c in self.setup_commands:
            self.logger.debug("executing setup command: " + repr(c))
            self.stash(c, persistent_level=1)
        self.stash("clear")

    def tearDown(self):
        assert self.stash.runtime.child_thread is None, "child thread is not cleared"
        assert len(self.stash.runtime.worker_registry) == 0, "worker registry not empty"
        del self.stash

    def do_test(
        self,
        cmd,
        cmp_str,
        ensure_same_cwd=True,
        ensure_undefined=(),
        ensure_defined=(),
        exitcode=None,
    ):
        saved_cwd = os.getcwd()
        self.logger.info("executing {c} in {d}...".format(c=cmd, d=saved_cwd))
        # 1 for mimicking running from console
        worker = self.stash(cmd, persistent_level=1)

        self.assertEqual(cmp_str, self.stash.main_screen.text, "output not identical")

        if exitcode is not None:
            self.assertEqual(worker.state.return_value, exitcode, "unexpected exitcode")
        else:
            self.logger.info("Exitcode: " + str(worker.state.return_value))

        if ensure_same_cwd:
            assert os.getcwd() == saved_cwd, "cwd changed"
        else:
            if os.getcwd() != saved_cwd:
                self.logger.warning(
                    "CWD changed from '{o}' to '{n}'!".format(
                        o=saved_cwd, n=os.getcwd()
                    )
                )

        for v in ensure_undefined:
            assert v not in self.stash.runtime.state.environ.keys(), (
                "%s should be undefined" % v
            )

        for v in ensure_defined:
            assert v in self.stash.runtime.state.environ.keys(), (
                "%s should be defined" % v
            )

    def run_command(self, command, exitcode=None):
        """
        Run a command and return its output.
        :param command: command to run
        :type command: str
        :param exitcode: expected exitcode, None to ignore
        :type exitcode: int or None
        :return: output of the command
        :rtype: str
        """
        # for debug purposes, locate script
        try:
            scriptname = command.split(" ")[0]
            scriptfile = self.stash.runtime.find_script_file(scriptname)
            self.logger.debug("Scriptfile for command: " + str(scriptfile))
        except Exception as e:
            self.logger.warning("Could not find script for command: " + repr(e))
            # do NOT return here, script may be alias
        outs = StringIO()
        self.logger.info("Executing: " + repr(command))
        worker = self.stash(
            command, persistent_level=1, final_outs=outs, final_errs=outs, cwd=self.cwd
        )  # 1 for mimicking running from console
        output = outs.getvalue()
        returnvalue = worker.state.return_value
        self.logger.debug(output)
        self.logger.debug("Exitcode: " + str(returnvalue))
        if exitcode is not None:
            self.assertEqual(
                returnvalue,
                exitcode,
                "unexpected exitcode ({e} expected, got {g})\nOutput:\n{o}\n".format(
                    e=exitcode, g=returnvalue, o=output
                ),
            )
        return output
