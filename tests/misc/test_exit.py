"""tests for the 'exit' command."""
from stash.tests.stashtest import StashTestCase

class ExitTests(StashTestCase):
    """Tests for the 'exit' command."""
    def test_help(self):
        """test 'exit --help'."""
        output = self.run_command("exit --help", exitcode=0)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("status", output)
        self.assertIn("exit", output)

    def test_exit_default(self):
        """test 'exit'."""
        output = self.run_command("exit", exitcode=0).replace("\n", "")
        self.assertEqual(output, "")

    def test_exit_0(self):
        """test 'exit 0'."""
        output = self.run_command("exit 0", exitcode=0).replace("\n", "")
        self.assertEqual(output, "")

    def test_exit_1(self):
        """test 'exit 1'."""
        output = self.run_command("exit 1", exitcode=1).replace("\n", "")
        self.assertEqual(output, "")

    def test_exit_0_to_255(self):
        """test 'exit {i}' where i = 0, ..., 255."""
        for i in range(256):
            output = self.run_command("exit " + str(i), exitcode=i).replace("\n", "")
            self.assertEqual(output, "")
