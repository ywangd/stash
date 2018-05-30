import os

from stash.tests.stashtest import StashTestCase


class Md5sumTests(StashTestCase):
    """tests for the md5sum command."""
    def setUp(self):
        """setup the tests"""
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def get_data_path(self):
        """return the data/ sibling path"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

    def test_help(self):
        """test md5sum --help"""
        output = self.run_command("md5sum --help", exitcode=0)
        # check for code words in output
        self.assertIn("md5sum", output)
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
            output = self.run_command("md5sum " + fullp, exitcode=0)
            result = output.split(" ")[0]
            self.assertEqual(result, expected_hash)

    def test_checkhash(self):
        """test md5sum -c"""
        output = self.run_command("md5sum -c results.md5sum", exitcode=0)
        self.assertIn("Pass", output)
        self.assertNotIn("Fail", output)

    def test_checkhash_fail(self):
        """test failure md5sum -c with invalid data"""
        output = self.run_command("md5sum -c wrong_results.md5sum", exitcode=1)
        self.assertIn("Pass", output)  # some files should have the correct hash
        self.assertIn("Fail", output)

    def test_hash_stdin_implicit(self):
        """test hashing of stdin without arg"""
        output = self.run_command("echo test | md5sum", exitcode=0).replace("\n", "")
        expected = "d8e8fca2dc0f896fd7cb4cb0031ba249"
        self.assertEqual(output, expected)

    def test_hash_stdin_explicit(self):
        """test hashing of stdin with '-' arg"""
        output = self.run_command("echo test | md5sum -", exitcode=0).replace("\n", "")
        expected = "d8e8fca2dc0f896fd7cb4cb0031ba249"
        self.assertEqual(output, expected)
