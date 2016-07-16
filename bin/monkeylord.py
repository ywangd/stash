"""easiliy manage monkey-patches"""
import argparse
import sys
from mlpatches import base

_stash = globals()["_stash"]
base._stash = _stash  # set before any other mlpatches import

from mlpatches import patches


def main(ns):
	if ns.action == "enable":
		if ns.name not in patches.PATCHES:
			print(
				_stash.text_color(
					"Error: Patch '{n}' not found!".format(n=ns.name),
					"red"
					)
				)
			sys.exit(1)
		patch = patches.PATCHES[ns.name]
		patch.enable()
	elif ns.action == "disable":
		if ns.name not in patches.PATCHES:
			print(
				_stash.text_color(
					"Error: Patch '{n}' not found!".format(n=ns.name),
					"red"
					)
				)
			sys.exit(1)
		patch = patches.PATCHES[ns.name]
		patch.disable()
			

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"action", choices=["enable", "disable"],
		help="What to do",
		)
	parser.add_argument(
		"name",
		help="patch to perform action on"
		)
	ns = parser.parse_args()
	main(ns)
