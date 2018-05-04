"""Extract a zip archive into a directory."""
from __future__ import print_function
import os
import sys
import zipfile
import argparse

def main(args):
    ap = argparse.ArgumentParser()

    ap.add_argument('-d', '--exdir', nargs='?', help='extract files into exdir')
    ap.add_argument('-v', '--verbose',
                    action='store_true',
                    help='be more chatty')
    ap.add_argument('-t', '--list',
                    action='store_true',
                    help='list the contents of an archive')
    ap.add_argument('zipfile',
                    help='zip file to be extracted')
    ns = ap.parse_args(args)

    if not os.path.isfile(ns.zipfile):
        print("%s: No such file" % ns.zipfile)

    else:
        # PK magic marker check
        with open(ns.zipfile, "rb") as f:
            try:
                pk_check = f.read(2)
            except:
                pk_check = ''

        if pk_check != b'PK':
            print("%s: does not appear to be a zip file" % ns.zipfile)
            sys.exit(1)

        if ns.list:
            location = ''
        else:
            if os.path.basename(ns.zipfile).lower().endswith('.zip'):
                altpath = os.path.splitext(os.path.basename(ns.zipfile))[0]
            else:
                altpath = os.path.basename(ns.zipfile) + '_unzipped'
            altpath = os.path.join(os.path.dirname(ns.zipfile), altpath)
            location = ns.exdir or altpath
            if (os.path.exists(location)) and not (os.path.isdir(location)):
                print("%s: destination is not a directory" % location)
                sys.exit(1)
            elif not os.path.exists(location):
                os.makedirs(location)

        with open(ns.zipfile, 'rb') as zipfp:
            try:
                zipf = zipfile.ZipFile(zipfp)
                # check for a leading directory common to all files and remove it
                dirnames = [os.path.join(os.path.dirname(x), '') for x in zipf.namelist()]
                common_dir = os.path.commonprefix(dirnames or ['/'])
                # Check to make sure there aren't 2 or more sub directories with the same prefix
                if not common_dir.endswith('/'):
                    common_dir = os.path.join(os.path.dirname(common_dir), '')
                for name in zipf.namelist():
                    data = zipf.read(name)
                    fn = name
                    if common_dir:
                        if fn.startswith(common_dir):
                            fn = fn.split(common_dir, 1)[-1]
                        elif fn.startswith('/' + common_dir):
                            fn = fn.split('/' + common_dir, 1)[-1]
                    fn = fn.lstrip('/')
                    fn = os.path.join(location, fn)
                    dirf = os.path.dirname(fn)

                    if not os.path.exists(dirf) and not ns.list:
                        os.makedirs(dirf)

                    if fn.endswith('/'):
                        # A directory
                        if not os.path.exists(fn) and not ns.list:
                            os.makedirs(fn)
                    elif not ns.list:
                        fp = open(fn, 'wb')
                        try:
                            fp.write(data)
                        finally:
                            fp.close()

                    if ns.verbose or ns.list:
                        print(fn)
            except:
                print("%s: zip file is corrupt" % ns.zipfile)


if __name__ == '__main__':
    main(sys.argv[1:])