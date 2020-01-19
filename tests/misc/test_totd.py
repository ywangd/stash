"""
Tests for the 'totd' command.
"""
from stash.tests.stashtest import StashTestCase


class TotdTests(StashTestCase):
    """
    Tests for the 'totd' command.
    """
    
    def test_help(self):
        """
        Test 'totd --help'.
        """
        output = self.run_command("totd --help", exitcode=0)
        self.assertIn("totd", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("-n", output)
        self.assertIn("--count", output)
    
    def test_count(self):
        """
        Test 'totd --count'.
        """
        output = self.run_command("totd --count", exitcode=0).replace("\n", "")
        # ensure that the string is correct
        self.assertTrue(output.startswith("Total available tips: "))
        # ensure that number of tips is not zero
        self.assertFalse(output.endswith(" "))
    
    def test_simple(self):
        """
        Test a simple 'totd' execution.
        Ensure that different totds are returned.
        """
        known = []
        n_unique = 0
        for i in range(100):
            output = self.run_command("totd", exitcode=0).replace("\n", "")
            if output not in known:
                known.append(output)
                n_unique += 1
        self.assertGreater(n_unique, 3)
            
