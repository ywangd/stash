"""dropbox utilities."""
import sys
import base64
import pickle

from dropbox import client, session

import keychain
import clipboard

from stashutils import core


DB_SERVICE = "DropBox"


def dropbox_setup(username, stdin, stdout):
	"""helper-interface to setup dropbox."""
	_stash = core.get_stash()
	Text = _stash.text_color  # alias
	stdout.write(Text("="*40+"\nDropbox-setup\n"+"="*25+"\n", "blue"))
	header = "This interface will help you setup the dropbox access"
	header += " for '{n}'.".format(n=Text(username, "blue"))
	abort = Text("abort", "yellow")
	choices = (
		"I already have an appkey+secret",
		"I dont have a appkey+secret", abort
		)
	choice = _menu(header, choices, stdin, stdout)
	if choice == 2:
		raise KeyboardInterrupt("Setup aborted.")
	elif choice == 0:
		pass
	elif choice == 1:
		stdout.write("Please read this. After reading, press enter to continue.\n")
		text1 = "To allow StaSh access to your dropbox, "
		text2 = "you will have to perform the following steps:\n"
		stdout.write(text1 + text2)
		stdout.write("  1) Create a dropbox account (if you dont have one yet)\n")
		stdout.write("  2) Upgrade your Account to a dropbox-developer account.\n")
		stdout.write("  3) Create a dropbox-app.\n")
		stdout.write("  4) Enter your app-key,app-secret and access-type here.\n")
		stdout.write(Text("Continue?", "yellow"))
		stdin.readline()
		while True:
			header = "Select action"
			choices = (
				"Register to dropbox",
				"Go to the developer-page",
				"proceed",
				abort)
			choice = _menu(header, choices, stdin, stdout)
			if choice == 0:
				_open_url("https://www.dropbox.com/register")
			elif choice == 1:
				_open_url("https://developer.dropbox.com")
			elif choice == 2:
				break
			elif choice == 3:
				raise KeyboardInterrupt("Setup aborted.")
	stdout.write("Enter app-key (leave empty to use clipboard):\n>")
	appkey = stdin.readline().strip()
	if len(appkey) == 0:
		appkey = clipboard.get()
		stdout.write("Using clipboard (length={l}).\n".format(l=len(appkey)))
	stdout.write("Enter app-secret (leave empty to use clipboard):\n>")
	appsecret = stdin.readline().strip()
	if len(appsecret) == 0:
		appsecret = clipboard.get()
		stdout.write("Using clipboard (length={l}).\n".format(l=len(appsecret)))
	while True:
		stdout.write("Enter access type (dropbox/app_folder):\n")
		accesstype = stdin.readline().strip()
		if accesstype not in ("dropbox", "app_folder"):
			text = Text(
				"Invalid access type! Valid values: 'dropbox' and 'app_folder'.\n", "red"
				)
			stdout.write(text)
		else:
			break
	stdout.write("Creating session... ")
	sess = session.DropboxSession(appkey, appsecret, accesstype)
	stdout.write(Text("Done", "green"))
	stdout.write(".\nObtaining request token... ")
	request_token = sess.obtain_request_token()
	stdout.write(Text("Done", "green"))
	stdout.write(".\nBuilding authorization-URL... ")
	url = sess.build_authorize_url(request_token)
	stdout.write(Text("Done", "green"))
	stdout.write(".\nPlease press enter after you allowed access.")
	_open_url(url)
	stdin.readline()
	stdout.write("Obtaining Access token... ")
	access_token = sess.obtain_access_token(request_token)
	stdout.write(Text("Done", "green"))
	stdout.write(".\nSaving... ")
	save_dropbox_data(
		username, appkey, appsecret, accesstype, access_token
		)
	stdout.write(Text("Done", "green"))
	stdout.write(".\n")
	return True


def save_dropbox_data(username, key, sec, access_type, access_token):
	"""saves dropbox access information for username."""
	data = {
		"app_key": key,
		"app_sec": sec,
		"access_type": access_type,
		"access_token_key": access_token.key,
		"access_token_sec": access_token.secret
	}
	dumped = pickle.dumps(data)
	encoded = base64.b64encode(dumped)
	keychain.set_password(DB_SERVICE, username, encoded)


def load_dropbox_data(username):
	"""load dropbox access information for username."""
	encoded = keychain.get_password(DB_SERVICE, username)
	if encoded is None:
		return None
	dumped = base64.b64decode(encoded)
	raw = pickle.loads(dumped)
	return raw


def get_dropbox_client(username, setup=True, stdin=None, stdout=None):
	"""
	checks wether a dropbox.DropboxClient is available for username.
	If it is, it is returned.
	Otherwise, if setup is True, a command-line setup is shown.
	The setup uses stdin and stout, both defaulting to the sys.std*.
	If no client was found and setup is False, none will be returned.
	"""
	if stdout is None:
		stdout = sys.stdout
	if stdin is None:
		stdin = sys.stdin
	data = load_dropbox_data(username)
	if data is None:
		stdout.write("\n")
		if not setup:
			return None
		dropbox_setup(username, stdin, stdout)
		data = load_dropbox_data(username)
	appkey = data["app_key"]
	appsec = data["app_sec"]
	act = data["access_type"]
	sess = session.DropboxSession(appkey, appsec, act)
	atk = data["access_token_key"]
	ats = data["access_token_sec"]
	# token=session.OAuthToken(atk,ats)
	sess.set_token(atk, ats)
	dbclient = client.DropboxClient(sess)
	return dbclient


def reset_dropbox(username):
	"""resets the dropbox configuration for the user username"""
	keychain.delete_password(DB_SERVICE, username)
	
		
def _menu(header, choices, stdin=None, stdout=None):
	"""a command-line menu."""
	if stdin is None:
		stdin = sys.stdin
	if stdout is None:
		stdout = sys.stdout
	assert len(choices) > 0, ValueError("No choices!")
	while True:
		stdout.write(header + "\n")
		for i, n in enumerate(choices):
			stdout.write("   {i: >3}: {n}\n".format(i=i, n=n))
		stdout.write("n?>")
		answer = stdin.readline().strip()
		try:
			answer = int(answer)
			return answer
		except (KeyError, ValueError, IndexError):
			stdout.write("\n"*20)


def _open_url(url):
	"""opens an url"""
	_stash = core.get_stash()
	_stash("webviewer {u}".format(u=url))