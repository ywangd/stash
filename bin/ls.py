# -*- coding: utf-8 -*-
"""List information about files (the current directory by default)"""
from __future__ import print_function
import os
import sys
import time
import tarfile
import zipfile
import imghdr
from argparse import ArgumentParser

from stashutils.mount_ctrl import get_manager


def is_mounted(path):
	"""checks if path is on a mounted path."""
	manager = get_manager()
	if not manager:
		return False
	fsi = manager.get_fsi(path)[0]
	return (fsi is not None)


def get_file_extension(path):
	"""returns the file extension of path"""
	if "." not in path:
		return ""
	else:
		return path.split(".")[-1].lower()


def is_archive(path):
	"""checks if path points to an archive"""
	if not is_mounted(path):
		arch = False
		try:
			arch = tarfile.is_tarfile(path)
		except:
			# not found
			pass
		try:
			arch = (arch or zipfile.is_zipfile(path))
		except:
			pass
		return arch
	else:
		fe = get_file_extension(path)
		if fe in ("zip", "rar", "tar", "bz2", "gz"):
			return True
		else:
			return False


def is_image(path):
	"""checks wether path points to an image."""
	if not is_mounted(path):
		try:
			return (imghdr.what(path) is not None)
		except:
			# continue execution outside of the if-statement
			pass
	fe = get_file_extension(path)
	if fe in (
		"rgb", "gif", "pbm", "pgm", "ppm", "tiff", "rast", "xbm",
		"jpeg", "jpg", "bmp", "png",
		):
		return True
	else:
		return False


def main(args):
    ap = ArgumentParser()
    ap.add_argument('-1', '--one-line', action='store_true', help='List one file per line')
    ap.add_argument('-a', '--all', action='store_true', help='do not ignore entries starting with .')
    ap.add_argument('-l', '--long', action='store_true', help='use a long listing format')
    ap.add_argument('files', nargs='*', help='files to be listed')
    ns = ap.parse_args(args)

    _stash = globals()['_stash']
    exitcode = 0
    sizeof_fmt = _stash.libcore.sizeof_fmt

    joiner = '\n' if ns.one_line or ns.long else ' '

    if ns.all:
        def _filter(filename):
            return True
    else:
        def _filter(filename):
            return False if filename.startswith('.') else True

    if ns.long:
        def _fmt(filename, dirname=''):
            _stat = os.stat(os.path.join(dirname, filename))

            fullpath = os.path.join(dirname, filename)
            if os.path.isdir(fullpath):
                filename = _stash.text_color(filename, 'blue')
            elif filename.endswith('.py'):
                filename = _stash.text_color(filename, 'green')
            elif is_archive(fullpath):
                filename = _stash.text_color(filename, 'red')
            elif is_image(fullpath):
                filename = _stash.text_color(filename, 'brown')

            ret = filename + _stash.text_color(
                ' (%s) %s' % (sizeof_fmt(_stat.st_size),
                              time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime))),
                'gray')

            return ret
    else:
        def _fmt(filename, dirname=''):
            fullpath = os.path.join(dirname, filename)
            if os.path.isdir(fullpath):
                return _stash.text_color(filename, 'blue')
            elif filename.endswith('.py'):
                return _stash.text_color(filename, 'green')
            elif is_archive(fullpath):
                return _stash.text_color(filename, 'red')
            elif is_image(fullpath):
                return _stash.text_color(filename, 'brown')
            else:
                return filename

    if len(ns.files) == 0:
        filenames =  [".", ".."] + os.listdir('.')
        out = joiner.join(_fmt(f) for f in filenames if _filter(f))
        print(out)

    else:
        out_dir = []
        out_file = []
        out_miss = []
        for f in ns.files:
            if not os.path.exists(f):
                out_miss.append('ls: %s: No such file or directory' % f)
                exitcode = 1
            elif os.path.isdir(f):
                filenames = [".", ".."] + os.listdir(f)
                fn = (f[:-1] if f.endswith("/") else f)
                out_dir.append('%s/:\n%s\n' %
                               (fn,
                                joiner.join(_fmt(sf, f) for sf in filenames if _filter(sf))))
            else:
                out_file.append(_fmt(f))

        for o in out_miss:
            print(o)
        print(joiner.join(out_file))
        if out_file:
            print("")
        for o in out_dir:
            print(o)
    sys.exit(exitcode)


if __name__ == '__main__':
    main(sys.argv[1:])