# -*- coding: utf-8 -*-
"""tests for the selfupdate command."""

from stash.tests.stashtest import StashTestCase, requires_network


class SelfupdateTests(StashTestCase):
    """
    Tests for the 'selfupdate' command.
    I have no idea how to test the actual selfupdate, so the tests
    currently only test 'selfupdate --check' and 'selfupdate --help'.
    """

    def test_help(self):
        """tests 'selfupdate --help'"""
        output = self.run_command("selfupdate --help", exitcode=0)
        self.assertIn("selfupdate", output)
        self.assertIn("usage", output)
        self.assertIn("-n", output)
        self.assertIn("--check", output)
        self.assertIn("-f", output)
        self.assertIn("--force", output)

    @requires_network
    def test_check_no_download(self):
        """ensures 'selfupdate --check' does not download anything."""
        output = self.run_command("selfupdate --check", exitcode=0)
        contains_latest_version = "Already at latest version" in output
        contains_new_version = "New version available" in output
        assert contains_latest_version or contains_new_version
        self.assertNotIn("Url: ", output)
        self.assertNotIn("Update completed.", output)
        self.assertNotIn("Failed to update. Please try again.", output)

    def test_default_repo_branch(self):
        """test that selfupdate uses the correct default repo and branch"""
        # network may be unavailable, but we are not interested anyway,
        # so we ignore the exitcode
        output = self.run_command("selfupdate --check", exitcode=None)
        self.assertIn("Target: ywangd:master", output)
        self.assertNotIn("Target: ywangd:dev", output)

    def test_default_repo(self):
        """test that selfupdate uses the correct default repo"""
        # network may be unavailable, but we are not interested anyway,
        # so we ignore the exitcode
        output = self.run_command("selfupdate --check dev", exitcode=None)
        self.assertIn("Target: ywangd:dev", output)
        self.assertNotIn("Target: ywangd:master", output)

    def test_SELFUPDATE_TARGET(self):
        """test that selfupdate uses the correct default repo"""
        # network may be unavailable, but we are not interested anyway,
        # so we ignore the exitcode
        output = self.run_command(
            "SELFUPDATE_TARGET=ywangd:dev selfupdate --check", exitcode=None
        )
        self.assertIn("Target: ywangd:dev", output)
        self.assertNotIn("Target: ywangd:master", output)

    def test_target_repo(self):
        """test that selfupdate uses the correct default repo"""
        # network may be unavailable, but we are not interested anyway,
        # so we ignore the exitcode
        output = self.run_command("selfupdate --check bennr01:dev", exitcode=None)
        self.assertIn("Target: bennr01:dev", output)
        self.assertNotIn("Target: ywangd:master", output)

    @requires_network
    def test_version_check_outdated(self):
        """test the version check on an outdated branch."""
        output = self.run_command(
            "selfupdate --check bennr01:selfupdate_test_outdated", exitcode=0
        )
        self.assertIn("Target: bennr01:selfupdate_test_outdated", output)
        self.assertNotIn("Target: ywangd:master", output)
        self.assertIn("Already at latest version", output)
        self.assertNotIn("New version available", output)
        self.assertNotIn("Error: ", output)

    @requires_network
    def test_version_check_update_available(self):
        """test the version check on an outdated branch."""
        output = self.run_command(
            "selfupdate --check bennr01:selfupdate_test_future", exitcode=0
        )
        self.assertIn("Target: bennr01:selfupdate_test_future", output)
        self.assertNotIn("Target: ywangd:master", output)
        self.assertNotIn("Already at latest version", output)
        self.assertIn("New version available", output)
        self.assertNotIn("Error: ", output)

    @requires_network
    def test_version_check_does_not_exist(self):
        """test the version check on an nonexistend branch."""
        output = self.run_command(
            "selfupdate --check selfupdate_test_does_not_exist", exitcode=0
        )
        self.assertIn("Target: ywangd:selfupdate_test_does_not_exist", output)
        self.assertNotIn("Target: ywangd:master", output)
        self.assertNotIn("Already at latest version", output)
        self.assertNotIn("New version available", output)
        self.assertIn("Error: ", output)
