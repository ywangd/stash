# -*- coding: utf-8 -*-
"""tests for the 'alias' command"""
from stash.tests.stashtest import StashTestCase


class AliasTests(StashTestCase):
	"""Tests for the 'alias' command."""
	def test_help(self):
		"""test 'alias --help'"""
		output = self.run_command("alias --help", exitcode=0)
		self.assertIn("alias", output)
		self.assertIn("-h", output)
		self.assertIn("--help", output)
		self.assertIn("name=", output)
	
	def test_logout_alias(self):
		"""tests the logout alias"""
		# assert existence
		output = self.run_command("alias", exitcode=0)
		self.assertIn("logout=", output)
		
		# assert output
		output = self.run_command("logout", exitcode=0)
		self.assertIn("exit StaSh.", output)
		self.assertNotIn("logout", output)
	
	def test_alias(self):
		"""create and test alias"""
		# ensure alias not yet defined
		output = self.run_command("alias", exitcode=0)
		self.assertNotIn("testalias", output)
		
		# create alias
		output = self.run_command("alias 'testalias=echo alias test successfull!'", exitcode=0)
		
		# ensure alias is defined
		output = self.run_command("alias", exitcode=0)
		self.assertIn("testalias=", output)
		
		# check output
		output = self.run_command("testalias", exitcode=0)
		self.assertIn("alias test successfull!", output)
