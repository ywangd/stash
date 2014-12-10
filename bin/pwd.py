import os
from argparse import ArgumentParser

ap = ArgumentParser()
ap.add_argument('-b', '--basename', action='store_true', help='Show basename only')

args = ap.parse_args()

curdir = os.getcwd()

if args.basename:
    print os.path.basename(curdir)
else:
    print curdir
