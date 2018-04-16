"""Simple FTP Server"""
from __future__ import print_function
from builtins import str
import argparse
import os
import sys
import threading
import time
import logging

_stash = globals()["_stash"]

try:
	import pyftpdlib
except ImportError:
	print("Installing pyftpdlib...")
	_stash("pip install pyftpdlib")
	es = os.getenv("?")
	if es != 0:
		print(_stash.text_color("Failed to install pyftpdlib!", "red"))
		sys.exit(1)

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.servers import FTPServer
from pyftpdlib.handlers import FTPHandler


def run(ns):
	"""starts the server."""
	auth = DummyAuthorizer()
	if ns.user is not None:
		auth.add_user(ns.user, ns.pswd, ns.path, perm=ns.perm)
	else:
		auth.add_anonymous(ns.path, perm=ns.perm)
	handler = FTPHandler
	handler.authorizer = auth
	handler.banner = "StaSh v{v} FTP-Server".format(v=_stash.__version__)
	address = ("0.0.0.0", ns.port)
	server = FTPServer(address, handler)
	server.max_cons = 128
	server.max_cons_per_ip = 128
	# setup logging
	logger = logging.getLogger("pyftpdlib")
	logger.setLevel(logging.CRITICAL)
	logger.propagate = False
	# server needs to run in a thread to be killable
	thr = threading.Thread(
		name="FTP-Server Thread", target=server.serve_forever
		)
	thr.daemon = True
	thr.start()
	print("FTP-Server started on {h}:{p}".format(h=address[0], p=str(address[1])))
	try:
		while True:
			time.sleep(0.2)
	except KeyboardInterrupt:
		print("Stopping Server...")
		server.close_all()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"-p", "--port", action="store", type=int,
		default=21, dest="port", help="port to listen on"
		)
	parser.add_argument(
		"-u", "--user", action="store", default=None, dest="user",
		help="username (default: anonymous)"
		)
	parser.add_argument(
		"--pswd", action="store", default=None, dest="pswd",
		help="password"
		)
	parser.add_argument(
		"--perm", action="store", default="elradfmwM", dest="perm",
		help="permissions of the user"
		)
	parser.add_argument(
		"--path", action="store", default=os.getcwd(), dest="path",
		help="path to serve"
		)
	ns = parser.parse_args()
	if (ns.user is not None) and (ns.pswd is None):
		print(
			_stash.text_color(
				"Error: If user is given, pswd must also be given!", "red"
				)
			)
		sys.exit(1)
	if (ns.pswd is not None) and (ns.user is None):
		print(
			_stash.text_color(
				"Error: If pswd is given, user must also be given!", "red"
				)
			)
		sys.exit(1)
	run(ns)
