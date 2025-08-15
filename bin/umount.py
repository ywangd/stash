# -*- coding: utf-8 -*-
"""unmount a filesystem."""

import argparse
import sys

from stashutils import mount_manager, mount_ctrl

_stash = globals()["_stash"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--all", action="store_true", dest="all", help="unmount all filesystems"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", dest="v", help="be more chatty"
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="force",
        help="force unmount; do not call fsi.close()",
    )
    parser.add_argument(
        "directory",
        action="store",
        nargs="?",
        default=None,
        help="directory to remove mounted filesystem from",
    )
    ns = parser.parse_args()

    if not (ns.directory or ("-a" in sys.argv) or ("--all" in sys.argv)):
        print(_stash.text_color("Error: no target directory specified!", "red"))
        sys.exit(1)

    manager = mount_ctrl.get_manager()

    if manager is None:
        manager = mount_manager.MountManager()
        mount_ctrl.set_manager(manager)

    if ns.all:
        to_unmount = [m[0] for m in manager.get_mounts()]
    else:
        to_unmount = [ns.directory]

    exitcode = 0

    for path in to_unmount:
        if ns.v:
            print("Unmounting '{p}'...".format(p=path))
        try:
            manager.unmount_fsi(path, force=ns.force)
        except mount_manager.MountError as e:
            exitcode = 1
            print(_stash.text_color("Error: {e}".format(e=e.message), "red"))
    if ns.v:
        print("Done.")
    sys.exit(exitcode)
