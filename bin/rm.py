import os
import sys
import shutil
from argparse import ArgumentParser


ap = ArgumentParser()
ap.add_argument('-r', '--recursive',
                action="store_true",
                default=False,
                help='remove directory and its contents recursively')
ap.add_argument('-i', '--interactive',
                action="store_true",
                default=False,
                help='prompt before every removal')
ap.add_argument('-v', '--verbose',
                action="store_true",
                default=False,
                help='explain what is being done')
ap.add_argument('paths', action="store", nargs='+', help='files or directories to delete')

args = ap.parse_args()

#setup print function
if args.verbose:
    def printp(text):
        print text
else:
    def printp(text):
        pass

if args.interactive:
    def prompt(file):
        result = raw_input('Delete %s? [Y,n]: ' % file)
        if result == 'Y' or result == 'y':
            return True
        else:
            return False
else:
    def prompt(file):
        return True


for path in args.paths:
    if os.path.isfile(path):
        if prompt(path):
            try:
                os.remove(path)
                printp('%s has been deleted' % path)
            except:
                print '%s: unable to remove' % path

    elif os.path.isdir(path) and args.recursive:
        if prompt(path):
            try:
                shutil.rmtree(path)
                printp('%s has been deleted' % path)
            except:
                print '%s: unable to remove' % path

    elif os.path.isdir(path):
        print '%s: is a directory' % path
    else:
        print '%s: does not exist' % path