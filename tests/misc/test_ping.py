# -*- coding: utf-8 -*-
"""tests for the ping command."""
import time
import unittest

from stash.tests.stashtest import StashTestCase, requires_network


class PingTests(StashTestCase):
    """tests for the 'ping' command."""

    def test_help(self):
        """test 'ping --help'"""
        output = self.run_command("ping --help", exitcode=0)
        self.assertIn("ping", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("-c", output)
        self.assertIn("--count", output)
        self.assertIn("-W", output)
        self.assertIn("--timeout", output)

    @unittest.expectedFailure
    @requires_network
    def test_ping_normal(self):
        """test 'ping <ip>'."""
        target = "8.8.8.8"
        output = self.run_command("ping " + target, exitcode=0)
        self.assertIn("got ping in " + target, output)
        self.assertNotIn("failed", output)

    @unittest.expectedFailure
    @requires_network
    def test_count(self):
        """test 'ping <target> --count <n>'."""
        target = "8.8.8.8"
        for n in (1, 3, 5):
            output = self.run_command(
                "ping " + target + " --count " + str(n), exitcode=0)
            self.assertIn("got ping in " + target, output)
            self.assertNotIn("failed", output)
            c = output.count("got ping in")
            self.assertEqaual(n, c)

    @unittest.expectedFailure
    @requires_network
    def test_interval(self):
        """test 'ping <target> --interval <n>'."""
        target = "8.8.8.8"
        c = 3
        for t in (1, 5, 10):
            st = time.time()
            output = self.run_command(
                "ping " +
                target +
                " --count " +
                str(c) +
                " --interval " +
                str(t),
                exitcode=0)
            et = time.time()
            dt = et - st
            self.assertIn("got ping in " + target, output)
            self.assertNotIn("failed", output)
            n = output.count("got ping in")
            self.assertEqaual(n, c)
            mintime = c * t
            maxtime = c * t + 5
            self.assertGreaterEqual(dt, mintime)
            self.assertLessEqual(dt, maxtime)

    @unittest.expectedFailure
    @unittest.skip("Test not implemented")
    def test_timeout():
        """test 'ping <target> --timeout <t>'."""
        # no idea how to implement a test for this case
        raise NotImplementedError
