import os
import shutil
import argparse

ap = argparse.ArgumentParser()
ap.add_argument('source', nargs='+', help='Source files to be moved')
ap.add_argument('target', nargs=1, help='Target file')
args = ap.parse_args()

def pprint(path):
    if path.startswith(os.environ['HOME']):
        return '~' + path.split(os.environ['HOME'], 1)[-1]
    return path

"""move files and directories"""
dest = args.target[0]
files = args.source

if len(files) > 1:
    # Moving multiple files, destination must be an existing directory.
    if not os.path.isdir(dest):
        print "%s: No such directory" % pprint(dest)
    else:
        full_dest = os.path.abspath(dest).rstrip('/') + '/'
        for filef in files:
            full_file = os.path.abspath(filef).rstrip('/')
            file_name = os.path.basename(full_file)
            new_name = os.path.join(full_dest, file_name)
            if not os.path.exists(full_file):
                print "! Error: Skipped, missing -", pprint(filef)
                continue
            try:
                os.rename(full_file, new_name)
            except Exception:
                print "%s: Unable to move" % pprint(filef)
else:
    # Moving a single file to a (pre-existing) directory or a file
    filef = files[0]
    full_file = os.path.abspath(filef).rstrip('/')
    file_name = os.path.basename(full_file)
    full_dest = os.path.abspath(dest).rstrip('/')
    if os.path.isdir(full_dest):
        if os.path.exists(full_file):
            try:
                shutil.move(full_file, full_dest + '/' + file_name)
            except:
                print "%s: Unable to move" % pprint(filef)
        else:
            print "%s: No such file" % pprint(filef)
    else:
        if os.path.exists(full_file):
            try:
                shutil.move(full_file, full_dest)
            except:
                print "%s: Unable to move" % pprint(filef)
        else:
            print "%s: No such file" % pprint(filef)
