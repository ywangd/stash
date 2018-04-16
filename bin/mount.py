"""mount a filesystem."""
from __future__ import print_function
import argparse
import sys

from stashutils import mount_manager
from stashutils.fsi.interfaces import FILESYSTEM_TYPES
from stashutils import mount_ctrl


_stash = globals()["_stash"]


def list_mounts():
	"""list all mounts"""
	manager = mount_ctrl.get_manager()
	if manager is None:
		manager = mount_manager.MountManager()
		mount_ctrl.set_manager(manager)
	
	mounts = manager.get_mounts()
	for p, fsi, readonly in mounts:
		print("{f} on {p}".format(f=fsi.repr(), p=p))


if __name__ == "__main__":
	if len(sys.argv) == 2 and ("-l" in sys.argv):
		list_mounts()
		sys.exit(0)
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"-l", "--show-labels", action="store_true", dest="list",
		help="show also filesystem labels"
		)
	parser.add_argument(
		"-v", "--verbose", action="store_true", dest="v",
		help="be more chatty"
		)
	parser.add_argument(
		"-y", "--yes", action="store_true", dest="yes",
		help="enable the monkeypatches without asking")
	parser.add_argument(
		"-f", "--fake", action="store_false", dest="do_mount",
		help="dry run; do not mount fs"
		)
	parser.add_argument(
		"-r", "--read-only", action="store_true", dest="readonly",
		help="mount the filesystem read-only"
		)
	parser.add_argument(
		"-t", "--type", action="store", dest="type", default=None,
		help="Type of the filesystem to mount"
		)
	parser.add_argument(
		"options", action="store", nargs="*",
		help="additional arguments for mounting the fs",
		default=[]
		)
	parser.add_argument(
		"dir", action="store", help="dir to mount to"
		)
	ns = parser.parse_args()
	
	if ns.type is None:
		print(_stash.text_color("Error: no FS-Type specified!", "red"))
		sys.exit(1)
	
	manager = mount_ctrl.get_manager()
	if manager is None:
		manager = mount_manager.MountManager()
		mount_ctrl.set_manager(manager)
	
	if not manager.check_patches_enabled():
		if not ns.yes:
			print(_stash.text_color("WARNING: ", "red"))
			print(_stash.text_color(
				"The 'mount'-command needs to enable a few monkeypatches.",
				"yellow"
				))
			print(_stash.text_color(
				"Monkeypatches may make the system unstable.", "yellow"
				))
			y = raw_input(
				_stash.text_color(
					"Do you want to enable these patches? (y/n)", "yellow"
					)
				).upper() == "Y"
			
			if not y:
				print(_stash.text_color(
					"Error: Monkeypatches not enabled!", "red"
					))
				sys.exit(1)
			manager.enable_patches()
		else:
			manager.enable_patches()
	
	if not ns.type in FILESYSTEM_TYPES:
		print(_stash.text_color(
			"Error: Unknown Filesystem-Type!", "red"
			))
		sys.exit(1)
	
	fsic = FILESYSTEM_TYPES[ns.type]
	if ns.v:
		logger = sys.stdout.write
		print("Creating FSI...")
	else:
		logger = None
	fsi = fsic(logger=logger)
	if ns.v:
		print("Connecting FSI...")
	msg = fsi.connect(*tuple(ns.options))
	if isinstance(msg, (str, unicode)):
		print(_stash.text_color(
			"Error: {m}".format(m=msg), "red"
			))
		sys.exit(1)
	if ns.do_mount:
		try:
			manager.mount_fsi(ns.dir, fsi, readonly=ns.readonly)
		except mount_manager.MountError as e:
			print(_stash.text_color("Error: {e}".format(e=e.message), "red"))
			try:
				if ns.v:
					print("unmounting FSI...")
				fsi.close()
			except Exception as e:
				print(_stash.text_color(
					"Error unmounting FSI: {e}".format(e=e.message), "red"
					))
			else:
				if ns.v:
					print("Finished cleanup.")
			sys.exit(1)
	else:
		# close fs
		fsi.close()
	if ns.v:
		print("Done.")
	
	if ns.list:
		list_mounts()