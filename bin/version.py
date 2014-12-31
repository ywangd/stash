""" Show information about this StaSh installation.
"""

import os
import time


def main():
    HOME = os.environ['HOME']
    STASH_ROOT = os.environ['STASH_ROOT']
    # The path is shown as both /private/var/mobile/... and /var/mobile/...
    HOME_ALT = os.path.dirname(os.path.dirname(STASH_ROOT))
    print 'StaSh v%s' % globals()['__version__']
    print 'root: %s' % STASH_ROOT.replace(HOME, '~').replace(HOME_ALT, '~')
    _stat = os.stat(os.path.join(STASH_ROOT, 'stash.py'))
    last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime))
    print 'stash.py: %s' % last_modified
    print 'SELFUPDATE_BRANCH: %s' % os.environ['SELFUPDATE_BRANCH']
    print 'BIN_PATH:'
    for p in os.environ['BIN_PATH'].split(':'):
        print '  %s' % p.replace(HOME, '~').replace(HOME_ALT, '~')

if __name__ == '__main__':
    main()
