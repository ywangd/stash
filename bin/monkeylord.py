"""easiliy manage monkey-patches"""
import argparse
import sys
from mlpatches import base

_stash = globals()["_stash"]
base._stash = _stash  # set before any other mlpatches import

from mlpatches import patches


def main(ns):
	if (ns.name is None) and (ns.action in ("enable", "disable")):
		print(
			_stash.text_color(
				"Error: action requires name to be defined!", "red"
				)
			)
		sys.exit(2)
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
	elif ns.action == "list":
		print(_stash.text_bold("Available Monkeypathes:"))
		mlength = max([len(e) for e in patches.PATCHES.keys()]) + 2
		for pn in sorted(patches.PATCHES.keys()):
			patch = patches.PATCHES[pn]
			tl = len(pn)
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
