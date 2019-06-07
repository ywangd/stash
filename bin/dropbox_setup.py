#! python2
# -*- coding: utf-8 -*-
# StaSh utility

"""manage your dropbox configuration."""

import cmd
import keychain
import sys

from stashutils import dbutils


_stash = globals()["_stash"]


class DropboxSetupCmd(cmd.Cmd):
	"""The command loop for managing the dropbox"""
	intro = _stash.text_color(
		"Welcome to the Dropbox Setup. Type 'help' for help.", "yellow"
		)
	prompt = _stash.text_color("(dbs)", "red")
	use_rawinput = False
	
	def do_exit(self, cmd):
		"""exit: quits the setup."""
		sys.exit(0)
	do_quit = do_EOF = do_exit

	def do_list(self, cmd):
		"""list: lists the dropbox usernames."""
		self.stdout.write("\n")
		for service, account in keychain.get_services():
			if service == dbutils.DB_SERVICE:
				self.stdout.write(account + "\n")
		self.stdout.write("\n")

	def do_del(self, cmd):
		"""del USERNAME: resets the dropbox for USERNAME."""
		dbutils.reset_dropbox(cmd)
	do_reset = do_del
	
	def do_add(self, cmd):
		"""add USERNAME: starts the setup for USERNAME."""
		if len(cmd) == 0:
			self.stdout.write(
				_stash.text_color("Error: expected an username.\n", "red")
				)
			return
		try:
			dbutils.dropbox_setup(cmd, self.stdin, self.stdout)
		except KeyboardInterrupt:
			self.stdout.write("\nSetup aborted.\n")
	do_edit = do_add


if __name__ == "__main__":
	cmdo = DropboxSetupCmd()
	cmdo.cmdloop()