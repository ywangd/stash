"""List information about files (the current directory by default)"""
import os
import sys
import time
import tarfile
import zipfile
import imghdr
from argparse import ArgumentParser


def is_archive(path):
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
            elif imghdr.what(fullpath) is not None:
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
            elif imghdr.what(fullpath) is not None:
                return _stash.text_color(filename, 'brown')
            else:
                return filename

    if len(ns.files) == 0:
        out = joiner.join(_fmt(f) for f in os.listdir('.') if _filter(f))
        print out

    else:
        out_dir = []
        out_file = []
        out_miss = []
        for f in ns.files:
            if not os.path.exists(f):
                out_miss.append('ls: %s: No such file or directory' % f)
                exitcode = 1
            elif os.path.isdir(f):
                out_dir.append('%s/:\n%s\n' %
                               (f,
                                joiner.join(_fmt(sf, f) for sf in os.listdir(f) if _filter(sf))))
            else:
                out_file.append(_fmt(f))

        for o in out_miss:
            print o
        print joiner.join(out_file)
        if out_file:
            print
        for o in out_dir:
            print o
    sys.exit(exitcode)


if __name__ == '__main__':
    main(sys.argv[1:])