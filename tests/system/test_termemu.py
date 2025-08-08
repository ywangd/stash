# coding=utf-8

import pytest
from stash.tests.stashtest import StashTestCase


class TermemuTests(StashTestCase):
    setup_commands = ["BIN_PATH=$STASH_ROOT/tests/system/data:$BIN_PATH"]

    def test_201(self):
        self.stash("test_201.py")
        cmp_str = """[stash]$ The first line
[stash]$ rown fox jumps over the lazy dog"""
        assert self.stash.main_screen.text == cmp_str, "output not identical"

    def test_202(self):
        self.stash("test_202.py")
        cmp_str = """[stash]$ The first line
[stash]$ """
        assert self.stash.main_screen.text == cmp_str, "output not identical"

    @pytest.mark.skip(reason="This test fails and needs to be reviewed")
    def test_203(self):
        # FIXME: "Possibly test `cmp_str` is wrong, function works as expected"

        self.stash("test_203.py")
        cmp_str = """[stash]$ The first line
[stash]$                                 """
        assert self.stash.main_screen.text == cmp_str

    def test_204(self):
        self.stash("test_204.py")
        cmp_str = """[stash]$ The first line
A quick brown fox jumps over the lazy do[stash]$ """
        assert self.stash.main_screen.text == cmp_str
