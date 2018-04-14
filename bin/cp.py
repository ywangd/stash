"""Copy a file or directory. Multiple source files may be specified if the destination is
an existing directory.
"""

from __future__ import print_function

import argparse
import os
import shutil
import sys


def pprint(path):
    if path.startswith(os.environ['HOME']):
        return '~' + path.split(os.environ['HOME'], 1)[-1]
    return path

def main(args):
    ap = argparse.ArgumentParser()
    ap.add_argument('source', nargs='+', help='one or more files or directories to be copied')
    ap.add_argument('dest', help='destination file or folder')
    ns = ap.parse_args(args)

    files = ns.source
    dest = ns.dest

    if len(files) > 1:
        # Copying multiple files, destination must be an existing directory.
        if os.path.isdir(dest):
            full_dest = os.path.abspath(dest)
            for filef in files:
                full_file = os.path.abspath(filef)
                file_name = os.path.basename(full_file)
                new_name  = os.path.join(full_dest, file_name)

                try:
                    if os.path.isdir(full_file):
                        shutil.copytree(full_file, new_name)
                    else:
                        shutil.copy(full_file, new_name)
                except Exception as err:
                    print("cp: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        else:
            print("cp: {}: No such directory".format(pprint(dest)), file=sys.stderr)
    else:
        # Copying a single file to a (pre-existing) directory or a file
        filef = files[0]
        full_file = os.path.abspath(filef)
        file_name = os.path.basename(full_file)
        full_dest = os.path.abspath(dest)
        new_name = os.path.join(full_dest, file_name)
        if os.path.exists(full_file):
            try:
                if os.path.exists(full_dest):
                    # Destination already exists
                    if os.path.isdir(full_dest):
                        # Destination is a directory
                        if os.path.isdir(full_file):
                            shutil.copytree(full_file, new_name)
                        else:
                            shutil.copy(full_file, new_name)
                    else:
                        # Destination is a file
                        shutil.copy(full_file, full_dest)
                else:
                    # Destination does not yet exist
                    if os.path.isdir(full_file):
                        # Source is a directory, destination should become a directory
                        shutil.copytree(full_file,full_dest)
                    else:
                        # Source is a file, destination should become a file
                        shutil.copy(full_file,full_dest)
            except Exception as err:
                print("cp: {}: {!s}".format(type(err).__name__, err), file=sys.stderr)
        else:
            print("cp: {}: No such file".format(pprint(filef)), file=sys.stderr)

if __name__ == "__main__":
    main(sys.argv[1:])
