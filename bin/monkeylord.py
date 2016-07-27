"""easiliy manage monkey-patches"""
import argparse
import sys
from mlpatches import base

_stash = globals()["_stash"]
base._stash = _stash  # set before any other mlpatches import

from mlpatches import patches


def main(ns):
	if (ns.name is None):
		if ns.action == "enable":
			name = "STABLE"
		elif ns.action == "disable":
			name = "ALL"
		else:
			name = "ALL"
	else:
		name = ns.name
	if ns.action == "enable":
		# enable a patch
		if name not in patches.PATCHES:
			print(
				_stash.text_color(
					"Error: Patch '{n}' not found!".format(n=name),
					"red"
					)
				)
			sys.exit(1)
		patch = patches.PATCHES[name]
		patch.enable()
	elif ns.action == "disable":
		# disable a patch
		if name not in patches.PATCHES:
			print(
				_stash.text_color(
					"Error: Patch '{n}' not found!".format(n=name),
					"red"
					)
				)
			sys.exit(1)
		patch = patches.PATCHES[name]
		patch.disable()
	elif ns.action == "list":
		# show monkeypatches and their state
		print(_stash.text_bold("Available Monkeypatches:"))
		mlength = max([len(e) for e in patches.PATCHES.keys()]) + 2
		for pn in sorted(patches.PATCHES.keys()):
			patch = patches.PATCHES[pn]
			if patch.enabled:
				t = "[enabled]"
				c = "green"
			else:
				t = "[disabled]"
				c = "red"
			print(
				"{n}{e}{s}".format(
					n=pn,
					e=" " * (mlength - len(pn)),
					s=_stash.text_color(t, c)
					)
				)
			

if __name__ == "__main__":
	# main code
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"action", choices=["enable", "disable", "list"],
		help="What to do",
		)
	parser.add_argument(
		"name",
		help="patch to perform action on",
		nargs="?",
		default=None,
		)
	ns = parser.parse_args()
	main(ns)
