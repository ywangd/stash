"""utility StaSh testcase for common methids"""
# coding=utf-8
import os
import unittest

from stash import stash

class StashTestCase(unittest.TestCase):
	"""A test case implementing utility methods for testing StaSh"""
	
	cwd = "$STASH_ROOT"
	setup_commands = []
	
	def setUp(self):
		self.stash = stash.StaSh()
		self.stash('cd ' + self.cwd)
		for c in self.setup_commands:
			self.stash(c)
		self.stash('clear')
		
	def tearDown(self):
		assert self.stash.runtime.child_thread is None, 'child thread is not cleared'
		assert len(self.stash.runtime.worker_registry) == 0, 'worker registry not empty'
		del self.stash
		
	def do_test(self, cmd, cmp_str, ensure_same_cwd=True, ensure_undefined=(), ensure_defined=(), exitcode=None):
	
		saved_cwd = os.getcwd()
		worker = self.stash(cmd, persistent_level=1)  # 1 for mimicking running from console
		
		assert cmp_str == self.stash.main_screen.text, 'output not identical'
		
		if exitcode is not None:
			assert worker.state.return_value == exitcode, "unexpected exitcode"
		
		if ensure_same_cwd:
			assert os.getcwd() == saved_cwd, 'cwd changed'
			
		for v in ensure_undefined:
			assert v not in self.stash.runtime.state.environ.keys(), '%s should be undefined' % v
			
		for v in ensure_defined:
			assert v in self.stash.runtime.state.environ.keys(), '%s should be defined' % v
