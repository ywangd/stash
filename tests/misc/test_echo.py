"""tests for the 'echo' command."""
from stash.tests.stashtest import StashTestCase


class EchoTests(StashTestCase):
	"""tests for the 'echo' command."""
	def do_echo(self, s):
		"""echo a string and return the echoed output."""
		return self.run_command("echo " + s, exitcode=0)
	
	def test_simple(self):
		"""test 'echo test'"""
		o = self.do_echo("test")
		self.assertEqual(o, "test\n")
	
	def test_multi(self):
		"""test 'echo test1 test2 test:'"""
		o = self.do_echo("test1 test2 test3")
		self.assertEqual(o, "test1 test2 test3\n")
	
	def test_help_ignore(self):
		"""test that -h and --help will be ignored by echo."""
		ho = self.do_echo("-h")
		self.assertEqual(ho, "-h\n")
		helpo = self.do_echo("--help")
		self.assertEqual(helpo, "--help\n")
	
	def test_empty(self):
		"""test the behavior without arguments."""
		output = self.run_command("echo", exitcode=0)
		self.assertEqual(output, "\n")