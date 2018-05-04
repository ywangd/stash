"""easiliy manage monkey-patches. See 'man monkeypatching' for more help."""
from __future__ import print_function
import argparse
import sys
import json
from mlpatches import base

_stash = globals()["_stash"]

from mlpatches import patches


def patch_is_compatible(patch):
	"""Return True if the patch is compatible."""
	if _stash.PY3:
		return patch.PY3
	else:
		return patch.PY2


def save_config(path):
	"""save the current config to path."""
	ts = {}
	for k in patches.PATCHES:
		v = patches.PATCHES[k].enabled
		ts[k] = v
	with open(path, "w") as f:
		json.dump(ts, f)


def load_config(path):
	"""load the config from path"""
	with open(path, "rU") as f:
		tl = json.load(f)
	patches.PATCHES["ALL"].disable()
	for k in sorted(tl):  # sort is important to load groups first
		v = tl[k]
		p = patches.PATCHES[k]
		if v:
			p.enable()
		else:
			p.disable()
	
		
def main(ns):
	if (ns.name is None):
		if ns.action == "enable":
			name = "STABLE"
		elif ns.action == "disable":
			name = "ALL"
		elif (ns.action == "loadconf") or (ns.action == "saveconf"):
			print(
				_stash.text_color(
					"Name/Path needs to be specified for this action!", "red"
					)
				)
			sys.exit(2)
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
		if not patch_is_compatible(patch):
			print(
				_stash.text_color(
					"Error: Patch '{n}' not compatible with this python version!".format(n=name),
					"red"
					)
				)
			sys.exit(1)
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
		if not patch_is_compatible(patch):
			print(
				_stash.text_color(
					"Error: Patch '{n}' not compatible with this python version!".format(n=name),
					"red"
					)
				)
			sys.exit(1)
		patch.disable()
	elif ns.action == "list":
		# show monkeypatches and their state
		print(_stash.text_bold("Available Monkeypatches:"))
		mlength = max([len(e) for e in patches.PATCHES.keys()]) + 2
		for pn in sorted(patches.PATCHES.keys()):
			patch = patches.PATCHES[pn]
			if not patch_is_compatible(patch):
				continue
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
	elif ns.action == "saveconf":
		save_config(name)
	elif ns.action == "loadconf":
		load_config(name)


if __name__ == "__main__":
	# main code
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"action", choices=["enable", "disable", "list", "loadconf", "saveconf"],
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