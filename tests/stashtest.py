"""utility StaSh testcase for common methids"""
# coding=utf-8
import os
import unittest
import logging

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from stash import stash
from stash.system.shcommon import _STASH_ROOT


class StashTestCase(unittest.TestCase):
    """A test case implementing utility methods for testing StaSh"""

    cwd = "$STASH_ROOT"
    setup_commands = []

    def setupClass(self):
        logging.basicConfig(level=logging.DEBUG)

    def setUp(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stash = stash.StaSh()
        if not "STASH_ROOT" in os.environ:
            self.logger.debug("Setting $STASH_ROOT to: " + repr(_STASH_ROOT))
            os.environ["STASH_ROOT"] = _STASH_ROOT
        self.logger.debug("Enabling tracebacks...")
        self.stash("stashconf py_traceback 1")
        self.cwd = os.path.abspath(os.path.expandvars(self.cwd))
        self.logger.info("Target CWD is: "+ str(self.cwd))
        self.stash('cd ' + self.cwd, persistent_level=1)
        self.logger.debug("After cd, CWD is: " + os.getcwd())
        for c in self.setup_commands:
            self.logger.debug("executing setup command: " + repr(c))
            self.stash(c, persistent_level=1)
        self.stash('clear')

    def tearDown(self):
        assert self.stash.runtime.child_thread is None, 'child thread is not cleared'
        assert len(self.stash.runtime.worker_registry) == 0, 'worker registry not empty'
        del self.stash

    def do_test(self, cmd, cmp_str, ensure_same_cwd=True, ensure_undefined=(), ensure_defined=(), exitcode=None):

        saved_cwd = os.getcwd()
        self.logger.info("executing {c} in {d}...".format(c=cmd, d=saved_cwd))
        worker = self.stash(cmd, persistent_level=1)  # 1 for mimicking running from console

        assert cmp_str == self.stash.main_screen.text, 'output not identical'

        if exitcode is not None:
            assert worker.state.return_value == exitcode, "unexpected exitcode"
        else:
            self.logger.info("Exitcode: " + str(worker.state.return_value))

        if ensure_same_cwd:
            assert os.getcwd() == saved_cwd, 'cwd changed'
        else:
            if os.getcwd() != saved_cwd:
                self.logger.warning("CWD changed from '{o}' to '{n}'!".format(o=saved_cwd, n=os.getcwd()))

        for v in ensure_undefined:
            assert v not in self.stash.runtime.state.environ.keys(), '%s should be undefined' % v

        for v in ensure_defined:
            assert v in self.stash.runtime.state.environ.keys(), '%s should be defined' % v

    def run_command(self, command, exitcode=None):
        """run a command and return its output."""
        # for debug purposes, locate script
        try:
            scriptname = command.split(" ")[0]
            scriptfile = self.stash.runtime.find_script_file(scriptname)
            self.logger.debug("Scriptfile for command: " + str(scriptfile))
        except Exception as e:
            self.logger.error("Could not find script for command: " + repr(e))
        outs = StringIO()
        self.logger.info("Executing: " + repr(command))
        worker = self.stash(command, persistent_level=1, final_outs=outs, final_errs=outs) #  1 for mimicking running from console
        output = outs.getvalue()
        returnvalue = worker.state.return_value
        self.logger.debug(output)
        self.logger.debug("Exitcode: " + str(returnvalue))
        if exitcode is not None:
            assert returnvalue == exitcode, "unexpected exitcode ({e} expected, got {g})\nOutput:\n{o}\n".format(e=exitcode, g=returnvalue, o=output)
        return output
