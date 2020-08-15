# -*- coding: utf-8 -*-
"""tests for the 'gci' command."""
import gc

from stash.tests.stashtest import StashTestCase


class GciTests(StashTestCase):
    """tests for the 'gci' command."""

    def setUp(self):
        """setup the tests."""
        StashTestCase.setUp(self)
        gc.enable()  # make sure gc is enabled.

    def test_help(self):
        """test 'gci --help'"""
        output = self.run_command("gci --help", exitcode=0)
        self.assertIn("gci", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("usage", output)
        self.assertIn("enable", output)
        self.assertIn("disable", output)
        self.assertIn("status", output)
        self.assertIn("collect", output)
        self.assertIn("threshold", output)
        self.assertIn("break", output)
        self.assertIn("debug", output)

    def test_status(self):
        """test 'gci status'"""
        output = self.run_command("gci status", exitcode=0)
        self.assertIn("GC status:", output)
        self.assertIn("Tracked objects:", output)
        self.assertIn("Size of tracked objects:", output)
        self.assertIn("Garbage:", output)
        self.assertIn("Size of garbage:", output)
        self.assertIn("Debug:", output)

    def test_enabled_by_default(self):
        """test 'gci status' reporting the gc as enabled by default."""
        output = self.run_command("gci status", exitcode=0)
        self.assertIn("GC status:", output)
        self.assertIn("Enabled", output)
        self.assertNotIn("Disabled", output)

    def test_disabled_status(self):
        """test 'gci status' reporting the gc as disabled."""
        assert gc.isenabled(), "Internal error: gc not enabled at test start!"
        gc.disable()
        output = self.run_command("gci status", exitcode=0)
        self.assertIn("GC status:", output)
        self.assertNotIn("Enabled", output)
        self.assertIn("Disabled", output)
        gc.enable()

    def test_disable(self):
        """test 'gci disable' reporting the gc as enabled by default."""
        assert gc.isenabled(), "Internal error: gc not enabled at test start!"
        self.run_command("gci disable", exitcode=0)
        assert not gc.isenabled(), "'gci disable' did not work!"
        gc.enable()

    def test_enable(self):
        """test 'gci disable' reporting the gc as enabled by default."""
        assert gc.isenabled(), "Internal error: gc not enabled at test start!"
        gc.disable()
        self.run_command("gci enable", exitcode=0)
        assert gc.isenabled(), "'gci enable' did not work!"

    def test_debug(self):
        """test 'gci debug'"""
        output = self.run_command("gci debug", exitcode=0).replace("\n", "")
        self.assertEqual(output, "Debug: 0")
        self.run_command("gci debug 1", exitcode=0)
        output = self.run_command("gci debug", exitcode=0).replace("\n", "")
        self.assertEqual(output, "Debug: 1")
        self.run_command("gci debug 0", exitcode=0)
        output = self.run_command("gci debug", exitcode=0).replace("\n", "")
        self.assertEqual(output, "Debug: 0")

    def test_collect(self):
        """test 'gci collect'."""
        # only check for exit code
        # TODO: make a better test
        output = self.run_command("gci collect", exitcode=0)
        self.assertEqual(output.replace("\n", ""), "")

    def test_break(self):
        """test 'gci break'."""
        if len(gc.garbage) == 0:
            eec = 1
            eo = "Error: No Garbage found!"
        else:
            eec = 0
            eo = ""
        output = self.run_command("gci break", exitcode=eec)
        self.assertEqual(output.replace("\n", ""), eo)

    def test_threshold(self):
        """test 'gci threshold'."""
        g1, g2, g3 = gc.get_threshold()

        output = self.run_command("gci threshold", exitcode=0)
        self.assertIn("G1: " + str(g1), output)
        self.assertIn("G2: " + str(g2), output)
        self.assertIn("G3: " + str(g3), output)

        n1 = g1 + 1
        n2 = g2 + 1
        n3 = g3 + 1
        output = self.run_command("gci threshold {} {} {}".format(n1, n2, n3), exitcode=0)
        self.assertEqual(output.replace("\n", ""), "")

        output = self.run_command("gci threshold", exitcode=0)
        self.assertIn("G1: " + str(n1), output)
        self.assertIn("G2: " + str(n2), output)
        self.assertIn("G3: " + str(n3), output)

        gc.set_threshold(g1, g2, g3)
        output = self.run_command("gci threshold", exitcode=0)
        self.assertIn("G1: " + str(g1), output)
        self.assertIn("G2: " + str(g2), output)
        self.assertIn("G3: " + str(g3), output)
