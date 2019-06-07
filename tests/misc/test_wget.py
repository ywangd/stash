# -*- coding: utf-8 -*-
"""tests for the 'wget' command."""
import os
import tempfile

from stash.tests.stashtest import StashTestCase, requires_network


class WgetTests(StashTestCase):
    """tests for the 'wget' command."""
    cwd = tempfile.gettempdir()
    download_target = "https://github.com/ywangd/stash/archive/master.zip"
    invalid_target = "https://github.com/bennr01/stash/archive/does_not_exist.zip"

    def tearDown(self):
        """clean up a test."""
        for fn in ("master.zip", "downloaded.zip", "does_not_exist.zip"):
            if os.path.exists(fn):
                os.remove(fn)
        StashTestCase.tearDown(self)

    def test_help(self):
        """test 'wget --help'."""
        output = self.run_command("wget --help", exitcode=0)
        self.assertIn("wget", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("url", output)
        self.assertIn("-o", output)
        self.assertIn("--output-file", output)

    @requires_network
    def test_simple(self):
        """test 'wget <url>'."""
        self.assertNotIn("master.zip", os.listdir(self.cwd))  # file should not already exists
        output = self.run_command("wget " + self.download_target, exitcode=0)
        self.assertIn("Opening: ", output)
        self.assertIn("Save as: master.zip", output)
        self.assertNotIn("Invalid url: ", output)
        self.assertIn("master.zip", os.listdir(self.cwd))

    @requires_network
    def test_outfile(self):
        """test 'wget <url> -o <f>'."""
        self.assertNotIn("downloaded.zip", os.listdir(self.cwd))  # file should not already exists
        output = self.run_command("wget -o downloaded.zip " + self.download_target, exitcode=0)
        self.assertIn("Save as: downloaded.zip", output)
        self.assertNotIn("Save as: master.zip", output)
        self.assertNotIn("Invalid url: ", output)
        self.assertIn("downloaded.zip", os.listdir(self.cwd))
        self.assertNotIn("Save as: master.zip", output)

    @requires_network
    def test_invalid_url(self):
        """test 'wget <some invalid url>'."""
        self.assertNotIn("does_not_exist.zip", os.listdir(self.cwd))  # file should not already exists
        output = self.run_command("wget " + self.invalid_target, exitcode=1)
        self.assertIn("Opening: ", output)
        self.assertNotIn("Save as: does_not_exist.zip", output)
        self.assertIn("Invalid url: ", output)
        self.assertNotIn("does_not_exist.zip", os.listdir(self.cwd))
