"""List information about files (the current directory by default)"""
import os
import sys
import time
from argparse import ArgumentParser


def sizeof_fmt(num):
    for x in ['B', 'KB', 'MB', 'GB']:
        if num < 1024.0:
            if (x == 'bytes'):
                return "%s %s" % (num, x)
            else:
                return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f%s" % (num, 'TB')


def main(args):

    ap = ArgumentParser()
    ap.add_argument('-1', '--one-line', action='store_true', help='List one file per line')
    ap.add_argument('-a', '--all', action='store_true', help='do not ignore entries starting with .')
    ap.add_argument('-l', '--long', action='store_true', help='use a long listing format')
    ap.add_argument('files', nargs='*', help='files to be listed')
    args = ap.parse_args(args)

    joiner = '\n' if args.one_line or args.long else ' '

    if args.all:
        def _filter(filename):
            return True
    else:
        def _filter(filename):
            return False if filename.startswith('.') else True

    if args.long:
        def _fmt(filename, dirname=''):
            _stat = os.stat(os.path.join(dirname, filename))
            ret = '%s%s (%s) %s' % (filename,
                                    '/' if os.path.isdir(os.path.join(dirname, filename)) else '',
                                    sizeof_fmt(_stat.st_size),
                                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime)))

            return ret
    else:
        def _fmt(filename, dirname=''):
            return filename + ('/' if os.path.isdir(os.path.join(dirname, filename)) else '')

    if len(args.files) == 0:
        out = joiner.join(_fmt(f) for f in os.listdir('.') if _filter(f))
        print out

    else:
        out_dir = []
        out_file = []
        out_miss = []
        for f in args.files:
            if not os.path.exists(f):
                out_miss.append('ls: %s: No such file or directory' % f)
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


if __name__ == '__main__':
    main(sys.argv[1:])
