import os
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('target', nargs=1, help='the directory to make')
ap.add_argument('-p', '--parents', action='store_true', default=False,
                help='make parent directories as needed')
args = ap.parse_args()

target = args.target[0]

if os.path.exists(target):
    print "%s: File exists" % target
else:
    try:
        if args.parents:
            os.makedirs(target)
        else:
            os.mkdir(target)
    except Exception:
        print "%s: Unable to create" % target
