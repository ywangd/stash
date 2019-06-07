# -*- coding: utf-8 -*-
"""tests for the 'pwd' command."""
import os

from stash.tests.stashtest import StashTestCase


class PwdTests(StashTestCase):
    """tests for the 'pwd' command."""
    cwd = os.path.expanduser("~")

    def test_help(self):
        """test 'pwd --help'."""
        output = self.run_command("pwd --help")
        self.assertIn("pwd", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("-b", output)
        self.assertIn("--basename", output)
        self.assertIn("-f", output)
        self.assertIn("--fullname", output)

    def test_pwd_collapseuser(self):
        """tests 'pwd'."""
        output = self.run_command("pwd").replace("\n", "").replace("/", "")
        self.assertEqual(output, "~")

    def test_pwd_fullname(self):
        """tests 'pwd --fullname'."""
        output = self.run_command("pwd --fullname").replace("\n", "")
        self.assertEqual(output, os.path.abspath(os.getcwd()))

    def test_pwd_basename(self):
        """tests 'pwd --basename'."""
        output = self.run_command("pwd --basename").replace("\n", "")
        self.assertEqual(output, os.path.basename(os.getcwd()))

