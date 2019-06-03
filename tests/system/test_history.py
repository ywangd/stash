"""Tests for stash.system.shhistory"""
# coding=utf-8

import os

from stash.system.shhistory import ShHistory
from stash.tests.stashtest import StashTestCase


class HistoryTests(StashTestCase):
	
    setup_commands = ['BIN_PATH=$STASH_ROOT/tests/system/data:$BIN_PATH']
    
    def get_data_path(self):
        """return the data/ sibling path"""
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    
    @property
    def history(self):
        """quick access to history"""
        return self.stash.runtime.history
    
    def setUp(self):
        StashTestCase.setUp(self)
        self.history.clear()
    
    def test_new_empty(self):
        """test that a new ShHistory is empty"""
        h = ShHistory(self.stash)  # should not create any problems
        self.assertEqual(len(h.getlist()), 0)
    
    def test_add_simple(self):
        """test ShHistory.add"""
        # 'test' should not be in history
        self.assertNotIn("test", self.history.getlist())
        # add it
        self.history.add("test")
        # should now be in history
        self.assertIn("test", self.history.getlist())
    
    def test_add_whitespace(self):
        """test that adding lines with whitespaces at the beginning depends on the settings"""
        # test ignoring lines starting with whitespaces
        self.history.hide_whitespace = True
        self.history.add("a")
        self.history.add(" b")
        self.history.add("c")
        # only 2 should have been added
        self.assertEqual(len(self.history.getlist()), 2)
        self.assertNotIn("b", self.history.getlist())
        self.assertNotIn(" b", self.history.getlist())
        self.assertIn("a", self.history.getlist())
        self.assertIn("c", self.history.getlist())
        
        # clean
        self.history.clear()
        
        # test ignoring lines starting with whitespaces
        self.history.hide_whitespace = False
        self.history.add("a")
        self.history.add(" b")
        self.history.add("c")
        # only 2 should have been added
        self.assertEqual(len(self.history.getlist()), 2)
        self.assertIn("b", self.history.getlist())
        self.assertNotIn(" b", self.history.getlist())  # whitespace should be stripped
        self.assertIn("a", self.history.getlist())
        self.assertIn("c", self.history.getlist())
    
    def test_add_doubble(self):
        """test adding a line twice in a row"""
        l = "testline"
        # test with disallowed double lines
        self.history.allow_double = False
        self.history.add(l)
        self.history.add(l)
        self.assertEqual(len(self.history.getlist()), 1)
        self.assertIn(l, self.history.getlist())
        
        # clean
        self.history.clear()
        
        # twice, but not in a row should still be allowed
        self.assertEqual(len(self.history.getlist()), 0)
        self.history.add(l)
        self.history.add("other line")
        self.history.add(l)
        self.assertEqual(len(self.history.getlist()), 3)
        
        # clear
        self.history.clear()
        
        # test with allowed double lines
        self.history.allow_double = True
        self.history.add(l)
        self.history.add(l)
        self.assertEqual(len(self.history.getlist()), 2)
        self.assertIn(l, self.history.getlist())
    
    def test_clear(self):
        """test ShHistory.clear()"""
        self.assertEqual(len(self.history.getlist()), 0)
        elements = ["a", "b", "c", "d"]
        for e in elements:
            self.history.add(e)
        self.assertEqual(len(self.history.getlist()), len(elements))
        self.history.clear()
        self.assertEqual(len(self.history.getlist()), 0)
    
    def test_getlist_base(self):
        """base tests for ShHistory.getlist()"""
        # list should be empty
        self.assertEqual(len(self.history.getlist()), 0)
        # after adding an item it should no longer be empty
        self.history.add("test")
        self.assertEqual(len(self.history.getlist()), 1)
        # after clean, getlist() should be empty again
        self.history.clear()
        self.assertEqual(len(self.history.getlist()), 0)
        # no results should be removed, unless add() drops them
        for e in ["a", "b", "a"]:
            self.history.add(e)
        self.assertEqual(len(self.history.getlist()), 3)
    
    def test_getlist_inversed_order(self):
        """test  to ensure that ShHistory.getlist() returns the list in inversed order"""
        # list should be empty
        self.assertEqual(len(self.history.getlist()), 0)
        # add elements
        for i in range(10):
            self.history.add(str(i))
        # get list
        l = self.history.getlist()
        self.assertEqual(len(l), 10)
        # ensure reverse order
        for e, i in zip(l, range(len(l) - 1, 0, -1)):
            self.assertEqual(int(e), i)
    
    def test_getlist_newlist(self):
        """test to ensure that getlist() creates a new list"""
        self.history.add("a")
        self.history.add("b")
        self.assertIsNot(self.history.getlist(), self.history.getlist())
    
    def test_swap(self):
        """test ShHistory.swap()"""
        # swap somewhere
        self.history.swap("h_1")
        # ensure empty
        self.assertEqual(len(self.history.getlist()), 0)
        # add element
        self.history.add("a")
        self.history.add("b")
        # no longer empty
        self.assertEqual(len(self.history.getlist()), 2)
        old_h1_list = self.history.getlist()
        # swap
        self.history.swap("h_2")
        # assert empty
        self.assertEqual(len(self.history.getlist()), 0)
        # add something
        self.history.add("c")
        # no longer empty
        self.assertEqual(len(self.history.getlist()), 1)
        old_h2_list = self.history.getlist()
        # swap back
        self.history.swap("h_1")
        # should still equal to old list
        new_h1_list = self.history.getlist()
        self.assertListEqual(old_h1_list, new_h1_list)
        # and back to h2
        self.history.swap("h_2")
        new_h2_list = self.history.getlist()
        self.assertListEqual(old_h2_list, new_h2_list)
    
    def test_save_load(self):
        """test saving and loading of the history"""
        elements = ["1", "2", "3", "4", "5"]
        filename = "history_test_s_l"
        # add elements
        for e in elements:
            self.history.add(e)
        # ensure correctly added
        self.assertEqual(len(self.history.getlist()), len(elements))
        # save
        self.history.save(filename)
        # assert no changes due to save
        self.assertEqual(len(self.history.getlist()), len(elements))
        # load
        h = ShHistory.load(filename, self.stash)
        # assert unique
        self.assertIsNot(h, self.history)
        # ensure all elements were loaded
        self.assertEqual(len(self.history.getlist()), len(elements))
        # ensure correct order
        self.assertListEqual(self.history.getlist(), h.getlist())
    
    def test_load_fail(self):
        """test that loading a nonexistent file fails"""
        p = "/does/not/exists"
        self.assertFalse(os.path.exists(p))
        with self.assertRaises(IOError):
            ShHistory.load(p, self.stash)
    
    def test_load_old(self):
        """test loading old histories"""
        p = os.path.join(self.get_data_path(), "old_history.txt")
        h = ShHistory.load(p, self.stash)
        # explicitly switch to StaSh.runtime
        self.history.swap("StaSh.runtime")
        expected = ["4", "3", "2", "1"]
        self.assertListEqual(h.getlist(), expected)
    
    # TODO: tests for .up(), .down() and .search()