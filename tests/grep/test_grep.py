# -*- coding: utf-8 -*-
"""tests for the 'grep' command"""
import os

from stash.tests.stashtest import StashTestCase


class GrepTests(StashTestCase):
    """ Tests for the 'grep' command
        No test cases for --color and --encoding.
        Everything else has a test case here. """

    def setUp(self):
        """setup the tests"""
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def get_data_path(self):
        """return the data/ sibling path"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))

    def test_grep_case(self):
        """test 'grep' case sensitivity."""
        output = self.run_command("grep 'grep' case_content.txt", exitcode=0)
        self.assertEqual("""test grep lower case test
test grep Grep GREP grep GREP Grep test
""",output)
        output = self.run_command("grep -i 'grep' case_content.txt", exitcode=0)
        self.assertEqual("""test grep lower case test
test Grep mixed case test
test GREP upper case test
test grep Grep GREP grep GREP Grep test
""",output)

    def test_grep_count(self):
        """ test 'grep' counting and file name display"""
        with self.subTest(flavor='--count single_file'):
            output = self.run_command("grep --count 'grep' case_content.txt", exitcode=0)
            self.assertEqual('2\n',output)
        with self.subTest(flavor='--count --with-filename single_file'):
            output = self.run_command("grep --count --with-filename 'grep' case_content.txt", exitcode=0)
            self.assertEqual('case_content.txt:2\n',output)
        with self.subTest(flavor='--count multiple_files'):
            output = self.run_command("grep --count 'grep' *.txt", exitcode=0)
            self.assertEqual(['',
                              'another_file.txt:1',
                              'case_content.txt:2',
                              'nothing_to_be_found.txt:0'],sorted(output.split('\n')))
        with self.subTest(flavor='--count --no-filename multiple_files'):
            output = self.run_command("grep --count --no-filename 'grep' case_content.txt nothing_to_be_found.txt another_file.txt", exitcode=0)
            self.assertEqual("2\n0\n1\n",output)

    def test_grep_text(self):
        """ test 'grep' text and file name display"""
        with self.subTest(flavor='single_file'):
            output = self.run_command("grep 'Grep' case_content.txt", exitcode=0)
            self.assertEqual('test Grep mixed case test\ntest grep Grep GREP grep GREP Grep test\n',output)
        with self.subTest(flavor='--with-filename single_file'):
            output = self.run_command("grep --with-filename 'Grep' case_content.txt", exitcode=0)
            self.assertEqual("""case_content.txt:test Grep mixed case test
case_content.txt:test grep Grep GREP grep GREP Grep test
""",output)
        with self.subTest(flavor='multiple_files'):
            output = self.run_command("grep 'Grep' case_content.txt nothing_to_be_found.txt another_file.txt", exitcode=0)
            self.assertEqual("""case_content.txt:test Grep mixed case test
case_content.txt:test grep Grep GREP grep GREP Grep test
another_file.txt:in a file to Grep through
""",output)
        with self.subTest(flavor='--no-filename multiple_files'):
            output = self.run_command("grep --no-filename 'Grep' case_content.txt nothing_to_be_found.txt another_file.txt", exitcode=0)
            self.assertEqual("""test Grep mixed case test
test grep Grep GREP grep GREP Grep test
in a file to Grep through
""",output)
            
    def test_grep_stdin(self):
        """ test 'grep' to grep through stdin """
        with self.subTest(flavor='just stdin'):
            output = self.run_command("grep 'Grep'",stdin_text="something\nto Grep\nthrough\n", exitcode=0)
            self.assertEqual("""to Grep\n""",output)
        with self.subTest(flavor='just stdin with label'):
            output = self.run_command("grep --label pipe -H 'Grep'",stdin_text="something\nto Grep\nthrough\n", exitcode=0)
            self.assertEqual("""pipe:to Grep\n""",output)
        with self.subTest(flavor='file and stdin'):
            output = self.run_command("grep 'Grep' case_content.txt - another_file.txt",stdin_text="something\nto Grep\nthrough", exitcode=0)
            self.assertEqual("""case_content.txt:test Grep mixed case test
case_content.txt:test grep Grep GREP grep GREP Grep test
<stdin>:to Grep
another_file.txt:in a file to Grep through
""",output)
     
    def test_grep_recursive(self):
        with self.subTest(flavor='without pattern'):
            output = self.run_command("grep -r 'grep' .", exitcode=0)
            self.assertEqual(sorted("""./.hidden:with something to find: grep
./case_content.txt:test grep lower case test
./case_content.txt:test grep Grep GREP grep GREP Grep test
./subdir/recursive.omit:this is not grep-ed with recursive pattern
./subdir/recursive.txt:this is grep-ed only with recursive setting
./file_to.omit:not to be grep-ed file content
./another_file.txt:another grep test1 grep test2
""".split('\n')),sorted(output.split('\n')))
            
        with self.subTest(flavor='with pattern'):
            output = self.run_command("grep -r 'grep' './*.txt'", exitcode=0) # attention: ./*.txt is single-quoted!!
            self.assertEqual(sorted("""./case_content.txt:test grep lower case test
./case_content.txt:test grep Grep GREP grep GREP Grep test
./subdir/recursive.txt:this is grep-ed only with recursive setting
./another_file.txt:another grep test1 grep test2
""".split('\n')),sorted(output.split('\n')))

    def test_grep_line_number(self):
        """ test 'grep' text with file name display and line number"""
        with self.subTest(flavor='--line-number single_file'):
            output = self.run_command("grep --line-number 'Grep' case_content.txt", exitcode=0)
            self.assertEqual('2:test Grep mixed case test\n4:test grep Grep GREP grep GREP Grep test\n',output)
        with self.subTest(flavor='--line-number --with-filename single_file'):
            output = self.run_command("grep --line-number --with-filename 'Grep' case_content.txt", exitcode=0)
            self.assertEqual("""case_content.txt:2:test Grep mixed case test
case_content.txt:4:test grep Grep GREP grep GREP Grep test
""",output)
        with self.subTest(flavor='--line-number multiple_files'):
            output = self.run_command("grep --line-number 'Grep' case_content.txt nothing_to_be_found.txt another_file.txt", exitcode=0)
            self.assertEqual("""case_content.txt:2:test Grep mixed case test
case_content.txt:4:test grep Grep GREP grep GREP Grep test
another_file.txt:3:in a file to Grep through
""",output)
        with self.subTest(flavor='--line-number --no-filename multiple_files'):
            output = self.run_command("grep --line-number --no-filename 'Grep' case_content.txt nothing_to_be_found.txt another_file.txt", exitcode=0)
            self.assertEqual("""2:test Grep mixed case test
4:test grep Grep GREP grep GREP Grep test
3:in a file to Grep through
""",output)
            
    def test_grep_just_filenames(self):
        with self.subTest(flavor='files without match'):
            output = self.run_command("grep --files-without-match 'grep' *.txt", exitcode=0)
            self.assertEqual("nothing_to_be_found.txt\n",output)
        with self.subTest(flavor='files without match and count'):
            output = self.run_command("grep --files-without-match --count 'grep' *.txt", exitcode=0)
            self.assertEqual(['','another_file.txt:1','case_content.txt:2','nothing_to_be_found.txt','nothing_to_be_found.txt:0'],sorted(output.split("\n")))
        with self.subTest(flavor='files with match'):
            output = self.run_command("grep --files-with-matches 'grep' *.txt", exitcode=0)
            self.assertEqual(['','another_file.txt','case_content.txt'],sorted(output.split("\n")))
        with self.subTest(flavor='files with matches and count'):
            output = self.run_command("grep --files-with-matches --count 'grep' *.txt", exitcode=0)
            self.assertEqual(['','another_file.txt','another_file.txt:1','case_content.txt','case_content.txt:2','nothing_to_be_found.txt:0'],sorted(output.split("\n")))
            
    def test_grep_only_matching(self):
        with self.subTest(flavor='only matching'):
            output = self.run_command("grep --only-matching 'grep\s*\w*' *.txt", exitcode=0)
            self.assertEqual(['',
                              'another_file.txt:grep test1',
                              'another_file.txt:grep test2',
                              'case_content.txt:grep GREP',
                              'case_content.txt:grep Grep',
                              'case_content.txt:grep lower'],sorted(output.split('\n')))
        with self.subTest(flavor='only matching with line numbers'):
            output = self.run_command("grep --line-number --only-matching 'grep\s*\w*' *.txt", exitcode=0)
            self.assertEqual(['',
                              'another_file.txt:1:grep test1',
                              'another_file.txt:1:grep test2',
                              'case_content.txt:1:grep lower',
                              'case_content.txt:4:grep GREP',
                              'case_content.txt:4:grep Grep'],sorted(output.split('\n')))
        
    def test_grep_invert(self):
        with self.subTest(flavor='invert single_file'):
            output = self.run_command("grep --invert 'Grep' case_content.txt", exitcode=0)
            self.assertEqual('test grep lower case test\ntest GREP upper case test\n',output)
        with self.subTest(flavor='invert files with matches'):
            output = self.run_command("grep --invert --files-with-matches 'Grep' *.txt", exitcode=0)
            self.assertEqual([ '','another_file.txt','case_content.txt','nothing_to_be_found.txt' ],sorted(output.split('\n')))
        with self.subTest(flavor='invert files without match'):
            output = self.run_command("grep --invert --files-without-match 'Grep' *.txt", exitcode=0)
            self.assertEqual([ '' ],sorted(output.split('\n')))
            