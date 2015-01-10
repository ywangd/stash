"""Extract a zip archive into a directory."""
import os
import sys
import zipfile
import argparse

ap = argparse.ArgumentParser()

ap.add_argument('-d', '--exdir', nargs='?', help='extract files into exdir')
ap.add_argument('-v', '--verbose', help='be more chatty')
ap.add_argument('zipfname', nargs=1, help='zip file to be extracted')
args = ap.parse_args()

zipfname = args.zipfname[0]

if not os.path.isfile(zipfname):
    print "%s: No such file" % zipfname

else:
    # PK magic marker check
    with open(zipfname) as f:
        try:
            pk_check = f.read(2)
        except:
            pk_check = ''

    if pk_check != 'PK':
        print "%s: does not appear to be a zip file" % zipfname
        sys.exit(1)

    if os.path.basename(zipfname).lower().endswith('.zip'):
        altpath = os.path.splitext(os.path.basename(zipfname))[0]
    else:
        altpath = os.path.basename(zipfname) + '_unzipped'

    altpath = os.path.join(os.path.dirname(zipfname), altpath)

    location = args.exdir or altpath

    if (os.path.exists(location)) and not (os.path.isdir(location)):
        print "%s: destination is not a directory" % location
        sys.exit(1)
    elif not os.path.exists(location):
        os.makedirs(location)

    print 'extracting to %s ' % location

    with open(zipfname, 'rb') as zipfp:
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
                if not os.path.exists(dirf):
                    os.makedirs(dirf)
                if fn.endswith('/'):
                    # A directory
                    if not os.path.exists(fn):
                        os.makedirs(fn)
                else:
                    fp = open(fn, 'wb')
                    try:
                        fp.write(data)
                    finally:
                        fp.close()
        except:
            print "%s: zip file is corrupt" % zipfname
