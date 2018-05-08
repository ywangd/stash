# coding=utf-8
import time

from six import StringIO

from stash.tests.stashtest import StashTestCase


class ThreadsTests(StashTestCase):
	
    setup_commands = ['BIN_PATH=$STASH_ROOT/tests/system/data:$BIN_PATH']

    def test_101(self):
        """
        background thread clears properly
        """
        self.stash('test_101_1.py &')
        time.sleep(4)
        cmp_str = r"""[stash]$ [stash]$ sleeping ... 0
sleeping ... 1
"""
        assert self.stash.main_screen.text == cmp_str, 'output not identical'

    def test_102(self):
        """
        Two parallel threads with same stdout should interleave
        """
        outs = StringIO()
        self.stash('test_102_1.py &', final_outs=outs)
        self.stash('test_102_2.py &', final_outs=outs)
        time.sleep(5)
        s = outs.getvalue()

        # Count the number of times the output switches between threads
        change_cnt = 0
        prev_line = None
        for cur_line in outs.getvalue().splitlines():
            if prev_line is None: 
                prev_line = cur_line
            elif prev_line != cur_line:
                change_cnt += 1
                prev_line = cur_line
        
        self.assertTrue(change_cnt > 2, 'Output do not interleave')

    def test_103(self):
        """
        Two threads in parallel with different stdout do not interfere
        """
        outs1 = StringIO()

        self.stash('test_102_1.py &', final_outs=outs1)
        self.stash('test_102_2.py')
        time.sleep(1)

        cmp_str1 = r"""[stash]$ [stash]$ test_102_2.py
test_102_2.py
test_102_2.py
test_102_2.py
test_102_2.py
[stash]$ """
        assert self.stash.main_screen.text == cmp_str1, 'output not identical'

        cmp_str2 = r"""test_102_1.py
test_102_1.py
test_102_1.py
test_102_1.py
test_102_1.py
"""
        assert outs1.getvalue() == cmp_str2, 'output not identical'