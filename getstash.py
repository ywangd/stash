# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import shutil
import sys
import requests
import zipfile

try:
    branch = locals()['_br']
except KeyError:
    branch = 'master'
try:
    repo = locals()['_owner']
except:
    repo = 'ywangd'

_IS_UPDATE = '_IS_UPDATE' in locals()

TMPDIR = os.environ.get('TMPDIR', os.environ.get('TMP'))
URL_ZIPFILE = 'https://github.com/{}/stash/archive/{}.zip'.format(repo, branch)
TEMP_ZIPFILE = os.path.join(TMPDIR, '{}.zip'.format(branch))
TEMP_PTI = os.path.join(TMPDIR, 'ptinstaller.py')
URL_PTI = 'https://raw.githubusercontent.com/ywangd/pythonista-tools-installer/master/ptinstaller.py'

print('Downloading {} ...'.format(URL_ZIPFILE))

try:
    r = requests.get(URL_ZIPFILE, stream=True)
    file_size = r.headers.get('Content-Length')
    if file_size is not None:
        file_size = int(file_size)

    with open(TEMP_ZIPFILE, 'wb') as outs:
        block_sz = 8192
        for chunk in r.iter_content(block_sz):
            outs.write(chunk)

    # Get Pythonista Tools Installer
    r = requests.get(URL_PTI)
    with open(TEMP_PTI, 'w') as outs:
        outs.write(r.text)

except Exception as e:
    sys.stderr.write('{}\n'.format(e))
    sys.stderr.write('Download failed! Please make sure internet connection is available.\n')
    sys.exit(1)

BASE_DIR = os.path.expanduser('~')
TARGET_DIR = os.path.join(BASE_DIR, 'Documents/site-packages/stash')
if not os.path.exists(TARGET_DIR):
    os.makedirs(TARGET_DIR)
print('Unzipping into %s ...' % TARGET_DIR)

with open(TEMP_ZIPFILE, 'rb') as ins:
    try:
        zipfp = zipfile.ZipFile(ins)
        for name in zipfp.namelist():
            data = zipfp.read(name)
            name = name.split('stash-%s/' % branch, 1)[-1]  # strip the top-level directory
            if name == '':  # skip top-level directory
                continue

            fname = os.path.join(TARGET_DIR, name)
            if fname.endswith('/'):  # A directory
                if not os.path.exists(fname):
                    os.makedirs(fname)
            else:
                fp = open(fname, 'wb')
                try:
                    fp.write(data)
                finally:
                    fp.close()
    except:
        sys.stderr.write('The zip file is corrupted. Pleases re-run the script.\n')
        sys.exit(1)

print('Preparing the folder structure ...')
# Move ptinstaller.py to bin
shutil.move(TEMP_PTI, os.path.join(TARGET_DIR, 'bin/ptinstaller.py'))

# Move launch script to Documents for easy access
shutil.move(os.path.join(TARGET_DIR, 'launch_stash.py'), os.path.join(BASE_DIR, 'Documents/launch_stash.py'))

# Remove setup files and possible legacy files
try:
    os.remove(TEMP_ZIPFILE)

    # shutil.rmtree(os.path.join(TARGET_DIR, 'tests'))  # TODO: maybe readd this line later

    unwanted_files = [
        'getstash.py',
        'run_tests.py',
        'testing.py',
        'dummyui.py',
        'dummyconsole.py',
        'bin/pcsm.py',
        'bin/bh.py',
        'bin/pythonista.py',
        'bin/cls.py',
        'stash.py',
        'lib/librunner.py'
    ]

    for fname in unwanted_files:
        os.remove(os.path.join(TARGET_DIR, fname))
except:
    pass

if not _IS_UPDATE:
    print('Installation completed.')
    print('Please Restart Pythonista and run launch_stash.py under the Home directory to start StaSh.')
