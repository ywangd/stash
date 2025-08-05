# -*- coding: utf-8 -*-
"""tests for the 'version' command."""

import platform

from stash.tests.stashtest import StashTestCase


class VersionTests(StashTestCase):
    """Tests for the 'version' command."""

    def test_keys(self):
        """ensure keys like 'core.py' are in the output of 'version'"""
        output = self.run_command("version", exitcode=0)
        self.assertIn("StaSh", output)
        self.assertIn("Python", output)
        self.assertIn("UI", output)
        self.assertIn("root", output)
        self.assertIn("core.py", output)
        # skip iOS version because we run the tests on linux (i think)
        self.assertIn("Platform", output)
        self.assertIn("SELFUPDATE_TARGET", output)
        self.assertIn("BIN_PATH", output)
        self.assertIn("PYTHONPATH", output)
        self.assertIn("Loaded libraries", output)

    def test_correct_py_version(self):
        """test that the correct python version will be reported."""
        output = self.run_command("version", exitcode=0)
        self.assertIn(platform.python_version(), output)

    def test_correct_stash_version(self):
        """test that the correct stash version will be reported."""
        output = self.run_command("version", exitcode=0)
        self.assertIn(self.stash.__version__, output)
