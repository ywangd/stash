""" Show information about this StaSh installation.
"""

import os
import sys
import time
import platform
import plistlib

_stash = globals()['_stash']
collapseuser = _stash.libcore.collapseuser


# Following functions for getting Pythonista and iOS version information are adapted from
# https://github.com/cclauss/Ten-lines-or-less/blob/master/pythonista_version.py
def pythonista_version():  # 2.0.1 (201000)
    plist = plistlib.readPlist(os.path.abspath(os.path.join(sys.executable, '..', 'Info.plist')))
    return '{CFBundleShortVersionString} ({CFBundleVersion})'.format(**plist)


def ios_version():  # 9.2 (64-bit iPad5,4)
    ios_ver, _, machine_model = platform.mac_ver()
    bit = platform.architecture()[0].rstrip('bit') + '-bit'
    return '{} ({} {})'.format(ios_ver, bit, machine_model)


def main():
    STASH_ROOT = os.environ['STASH_ROOT']
    print(_stash.text_style('StaSh v%s' % globals()['_stash'].__version__,
                            {'color': 'blue', 'traits': ['bold']}))
    print(u'%s %s' % (_stash.text_bold('Pythonista'),
                      pythonista_version()))
    print(u'%s %s' % (_stash.text_bold('iOS'),
                      ios_version()))
    print(u'%s %s' % (_stash.text_bold('Python'), os.environ['STASH_PY_VERSION']))
    print(u'%s: %s' % (_stash.text_bold('root'), collapseuser(STASH_ROOT)))
    _stat = os.stat(os.path.join(STASH_ROOT, 'core.py'))
    last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime))
    print(u'%s: %s' % (_stash.text_bold('core.py'), last_modified))
    print(u'%s: %s' % (_stash.text_bold('SELFUPDATE_BRANCH'),
                       os.environ['SELFUPDATE_BRANCH']))
    print(_stash.text_bold('BIN_PATH:'))
    for p in os.environ['BIN_PATH'].split(':'):
        print('  %s' % collapseuser(p))


if __name__ == '__main__':
    main()