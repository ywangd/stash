# -*- coding: utf-8 -*-
import os

from stash.tests.stashtest import StashTestCase


class Sha256sumTests(StashTestCase):
    """tests for the sha256sum command."""
    def setUp(self):
        """setup the tests"""
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def get_data_path(self):
        """return the data/ sibling path"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

    def test_help(self):
        """test sha256sum --help"""
        output = self.run_command("sha256sum --help", exitcode=0)
        # check for code words in output
        self.assertIn("sha256sum", output)
        self.assertIn("-h", output)
        self.assertIn("-c", output)

    def test_filehash(self):
        """tests the hashes of the files in data/"""
        fp = self.get_data_path()
        for fn in os.listdir(fp):
            if "." in fn:
                # file used for something else
                continue
            expected_hash = fn
            fullp = os.path.join(fp, fn)
            output = self.run_command("sha256sum " + fullp, exitcode=0)
            result = output.split(" ")[0]
            self.assertEqual(result, expected_hash)

    def test_checkhash(self):
        """test sha256sum -c"""
        output = self.run_command("sha256sum -c results.sha256sum", exitcode=0)
        self.assertIn("Pass", output)
        self.assertNotIn("Fail", output)

    def test_checkhash_fail(self):
        """test failure sha256sum -c with invalid data"""
        output = self.run_command("sha256sum -c wrong_results.sha256sum", exitcode=1)
        self.assertIn("Pass", output)  # some files should have the correct hash
        self.assertIn("Fail", output)

    def test_hash_stdin_implicit(self):
        """test hashing of stdin without arg"""
        output = self.run_command("echo test | sha256sum", exitcode=0).replace("\n", "")
        expected = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
        self.assertEqual(output, expected)

    def test_hash_stdin_explicit(self):
        """test hashing of stdin with '-' arg"""
        output = self.run_command("echo test | sha256sum -", exitcode=0).replace("\n", "")
        expected = "f2ca1bb6c7e907d06dafe4687e579fce76b37e4e93b7605022da52e6ccc26fd2"
        self.assertEqual(output, expected)
