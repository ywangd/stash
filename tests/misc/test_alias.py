# -*- coding: utf-8 -*-
"""tests for the 'alias' command"""

from stash.tests.stashtest import StashTestCase


class AliasTests(StashTestCase):
    """Tests for the 'alias' command."""

    def test_help(self):
        """test 'alias --help'"""
        output = self.run_command("alias --help", exitcode=0)
        self.assertIn("alias", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("name=", output)

    def test_la_alias(self):
        """tests the unmount alias"""
        # assert existence
        output = self.run_command("alias", exitcode=0)
        self.assertIn("la=", output)

        # assert output identical
        output = self.run_command("la", exitcode=0)
        output_full = self.run_command("ls -a", exitcode=0)
        self.assertEqual(output, output_full)

    def test_alias(self):
        """create and test alias"""
        # ensure alias not yet defined
        output = self.run_command("alias", exitcode=0)
        self.assertNotIn("testalias", output)

        # create alias
        output = self.run_command(
            "alias 'testalias=echo alias test successfull!'", exitcode=0
        )

        # ensure alias is defined
        output = self.run_command("alias", exitcode=0)
        self.assertIn("testalias=", output)

        # check output
        output = self.run_command("testalias", exitcode=0)
        self.assertIn("alias test successfull!", output)
