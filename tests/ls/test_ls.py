# -*- coding: utf-8 -*-
"""tests for the 'ls' command"""
import os

from stash.tests.stashtest import StashTestCase


class LsTests(StashTestCase):
    """Tests for the 'ls' command."""

    def setUp(self):
        """setup the tests"""
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def get_data_path(self):
        """return the data/ sibling path"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

    def test_ls_cwd(self):
        """test 'ls' of data/ sibling dir without specified path."""
        output = self.run_command("ls", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_abspath(self):
        """test 'ls' of data/ sibling dir with specified absolute path."""
        output = self.run_command("ls " + self.get_data_path(), exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_relpath_1(self):
        """test 'ls' of data/ sibling dir with specified relative path '.'."""
        output = self.run_command("ls .", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_ls_relpath_2(self):
        """test 'ls' of data/ sibling dir with specified relative path '../data/'."""
        output = self.run_command("ls ../data/", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn(".hidden", output)

    def test_hidden(self):
        """test 'ls' behavior with hidden dotfiles."""
        # 1. test ignoring
        output = self.run_command("ls", exitcode=0)
        self.assertNotIn(".hidden", output)
        # 2. test -a
        output = self.run_command("ls -a", exitcode=0)
        self.assertIn(".hidden", output)
        self.assertIn(". ", output)
        self.assertIn(".. ", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        # 3. test -A
        output = self.run_command("ls -A", exitcode=0)
        self.assertIn(".hidden", output)
        self.assertNotIn(". ", output)
        self.assertNotIn(".. ", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)

    def test_ls_filename(self):
        """test 'ls file1.txt file2.txt' showing 'file1.txt file2.txt'"""
        output = self.run_command("ls file1.txt file2.txt", exitcode=0)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertNotIn("otherfile.txt", output)

    def test_oneline(self):
        """test 'ls -1'"""
        output = self.run_command("ls -1", exitcode=0)
        self.assertIn("file1.txt\n", output)
        self.assertIn("file2.txt\n", output)
        self.assertIn("otherfile.txt\n", output)
        self.assertNotIn(".hidden", output)

    def test_long(self):
        """test 'ls -l'"""
        output = self.run_command("ls -l", exitcode=0)
        # we cant test the complete output, but we can still test for
        # filename existence and exitcode
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertIn("otherfile.txt", output)
        self.assertNotIn(".hidden", output)

    def test_la(self):
        """test the 'la' alias for 'ls -a'"""
        output = self.run_command("la", exitcode=0)
        self.assertIn(".hidden", output)
        self.assertIn(".", output)
        self.assertIn("..", output)
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)

    def test_ll(self):
        """test the 'll' alias for 'ls -l'"""
        output = self.run_command("ll", exitcode=0)
        # we cant test the complete output, but we can still test for
        # filename existence and exitcode
        self.assertIn("file1.txt", output)
        self.assertIn("file2.txt", output)
        self.assertIn("otherfile.txt", output)
        self.assertIn(".hidden", output)
