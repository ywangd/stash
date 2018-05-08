# coding=utf-8
import os
import unittest

from stash.tests.stashtest import StashTestCase

class ExpanderTests(unittest.TestCase):

    def setUp(self):
        StashTestCase.setUp(self)
        self.expand = self.stash.runtime.expander.expand

    def _get_pipe_sequence(self, line):
        expanded = self.expand(line)
        next(expanded)
        return next(expanded)

    def test_envars(self):
        pipe_sequence = self._get_pipe_sequence(r'ls $SELFUPDATE_BRANCH')
        assert pipe_sequence.lst[0].args[0] == 'master'

    def test_tilda(self):
        pipe_sequence = self._get_pipe_sequence(r'ls ~/')
        assert pipe_sequence.lst[0].args[0] == os.path.expanduser('~/')

    def test_wildcards(self):
        pipe_sequence = self._get_pipe_sequence(r'ls *')
        assert 'README.md' in pipe_sequence.lst[0].args
        assert 'CHANGES.md' in pipe_sequence.lst[0].args

        pipe_sequence = self._get_pipe_sequence(r'ls README.?d')
        assert pipe_sequence.lst[0].args[0] == 'README.md'

        pipe_sequence = self._get_pipe_sequence(r'ls *stash*')
        # assert 'stash.py' in pipe_sequence.lst[0].args
        assert 'getstash.py' in pipe_sequence.lst[0].args
        assert 'launch_stash.py' in pipe_sequence.lst[0].args

        pipe_sequence = self._get_pipe_sequence(r'ls stash*')
        assert 'getstash.py' not in pipe_sequence.lst[0].args

    def test_escapes(self):
        pipe_sequence = self._get_pipe_sequence(r'ls \n')
        assert pipe_sequence.lst[0].args[0] == '\n'

        pipe_sequence = self._get_pipe_sequence(r'ls \033[32m')
        assert pipe_sequence.lst[0].args[0] == '\033[32m'

        pipe_sequence = self._get_pipe_sequence(r'ls \x1b[32m')
        assert pipe_sequence.lst[0].args[0] == '\x1b[32m'

    def test_double_quotes(self):
        pipe_sequence = self._get_pipe_sequence(r'ls "$SELFUPDATE_BRANCH"')
        assert pipe_sequence.lst[0].args[0] == 'master'

        pipe_sequence = self._get_pipe_sequence(r'ls "~/"')
        assert pipe_sequence.lst[0].args[0] == '~/'

        pipe_sequence = self._get_pipe_sequence(r'ls "*"')
        assert pipe_sequence.lst[0].args[0] == '*'

        pipe_sequence = self._get_pipe_sequence(r'ls "\033[32m"')
        assert pipe_sequence.lst[0].args[0] == '\033[32m'

    def test_single_quotes(self):
        pipe_sequence = self._get_pipe_sequence(r"ls '$SELFUPDATE_BRANCH'")
        assert pipe_sequence.lst[0].args[0] == '$SELFUPDATE_BRANCH'

        pipe_sequence = self._get_pipe_sequence(r'ls "~/"')
        assert pipe_sequence.lst[0].args[0] == '~/'

        pipe_sequence = self._get_pipe_sequence(r"ls '*'")
        assert pipe_sequence.lst[0].args[0] == '*'

        pipe_sequence = self._get_pipe_sequence(r"ls '\033[32m'")
        assert pipe_sequence.lst[0].args[0] == '\\033[32m'

    def test_redirect_file(self):
        pipe_sequence = self._get_pipe_sequence(r'ls >> somefile')
        cmd = pipe_sequence.lst[0]
        assert cmd.cmd_word == 'ls'
        assert cmd.args == []
        assert cmd.io_redirect.operator == '>>'
        assert cmd.io_redirect.filename == 'somefile'

    def test_redirect_file_descriptor(self):
        pipe_sequence = self._get_pipe_sequence(r'ls -1 > &3')
        cmd = pipe_sequence.lst[0]
        assert cmd.cmd_word == 'ls'
        assert cmd.args[0] == '-1' and len(cmd.args) == 1
        assert cmd.io_redirect.operator == '>'
        assert cmd.io_redirect.filename == '&3'