"""
Tests for pbcopy/pbpaste commands.
"""

import os
import tempfile
from io import open

from stash.tests.stashtest import StashTestCase


class CopyPasteTests(StashTestCase):
    """
    Test class for the 'pbcopy' and 'pbpaste' commands.
    """

    def test_pbcopy_help(self):
        """
        test 'pbcopy --help'.
        """
        output_1 = self.run_command("pbcopy -h", exitcode=0)
        output_2 = self.run_command("pbcopy --help", exitcode=0)
        self.assertEqual(output_1, output_2)
        self.assertIn("-h", output_1)
        self.assertIn("--help", output_1)
        self.assertIn("file", output_1)
        self.assertIn("pbcopy", output_1)
        self.assertIn("...", output_1)

    def test_pbpaste_help(self):
        """
        test 'pbpaste --help'.
        """
        output_1 = self.run_command("pbpaste -h", exitcode=0)
        output_2 = self.run_command("pbpaste --help", exitcode=0)
        self.assertEqual(output_1, output_2)
        self.assertIn("-h", output_1)
        self.assertIn("--help", output_1)
        self.assertIn("file", output_1)
        self.assertIn("pbpaste", output_1)

    def test_copy_paste_stdin(self):
        """
        Test copy of stdin & paste
        """
        self.run_command("echo teststring | pbcopy", exitcode=0)
        output = self.run_command("pbpaste", exitcode=0)
        self.assertEqual("teststring\n", output)

    def test_copy_paste_file(self):
        """
        Test copy of a file & paste
        """
        p = os.path.join(self.get_data_path(), "testfile.txt")
        self.run_command("pbcopy " + p, exitcode=0)
        output = self.run_command("pbpaste", exitcode=0)
        with open(p, "r", encoding="utf-8") as fin:
            content = fin.read()
        self.assertEqual(output, content)

    def test_paste_into_file(self):
        """
        Test copy of a file & paste into a file.
        Comparsion is done using 'md5sum'
        """
        pin = os.path.join(self.get_data_path(), "testfile.txt")
        pout = os.path.join(tempfile.gettempdir(), "testpastefile.txt")
        if os.path.exists(pout):
            os.remove(pout)
        self.run_command("pbcopy " + pin, exitcode=0)
        self.run_command("pbpaste " + pout, exitcode=0)
        org_hash = self.run_command("md5sum " + pin, exitcode=0).split()[0]
        paste_hash = self.run_command("md5sum " + pout, exitcode=0).split()[0]
        self.assertEqual(org_hash, paste_hash)
