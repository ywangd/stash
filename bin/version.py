""" Show information about this StaSh installation.
"""

import os
import time

_stash = globals()['_stash']
collapseuser = _stash.libcore.collapseuser

def main():
    STASH_ROOT = os.environ['STASH_ROOT']
    print _stash.text_style('StaSh v%s' % globals()['__version__'],
                            {'color': 'blue', 'traits': ['bold']})
    print u'%s: %s' % (_stash.text_bold('root'), collapseuser(STASH_ROOT))
    _stat = os.stat(os.path.join(STASH_ROOT, 'stash.py'))
    last_modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(_stat.st_mtime))
    print u'%s: %s' % (_stash.text_bold('stash.py'), last_modified)
    print u'%s: %s' % (_stash.text_bold('SELFUPDATE_BRANCH'),
                       os.environ['SELFUPDATE_BRANCH'])
    print _stash.text_bold('BIN_PATH:')
    for p in os.environ['BIN_PATH'].split(':'):
        print '  %s' % collapseuser(p)

if __name__ == '__main__':
    main()
