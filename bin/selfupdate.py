# coding=utf-8
"""
Selfupdate StaSh from the GitHub repo.

Usage: selfupdate.py [branch]

       branch: default to master
"""
import os
import sys
from argparse import ArgumentParser

_stash = globals()['_stash']

def main(args):

    ap = ArgumentParser()
    ap.add_argument('branch', nargs='?', help='The branch to update to')
    ns = ap.parse_args(args)

    if ns.branch is not None:
        SELFUPDATE_BRANCH = ns.branch
    else:
        SELFUPDATE_BRANCH = os.environ.get('SELFUPDATE_BRANCH', 'master')

    print _stash.text_style('StaSh is trying to selfupdate ...',
                            {'color': 'yellow', 'traits': ['bold']})
    print u'%s: %s' % (_stash.text_bold('branch'), SELFUPDATE_BRANCH)

    url = 'https://raw.githubusercontent.com/ywangd/stash/%s/getstash.py' % SELFUPDATE_BRANCH
    print u'%s: %s' % (_stash.text_bold('url'),
                       _stash.text_style(url, {'color': 'blue', 'traits': ['underline']}))

    import urllib2
    from random import randint

    try:
        exec urllib2.urlopen(
            'https://raw.githubusercontent.com/ywangd/stash/%s/getstash.py?q=%s' % (SELFUPDATE_BRANCH,
                                                                                    randint(1, 999999))
        ).read() in {'_IS_UPDATE': True, '_br': SELFUPDATE_BRANCH}
        print _stash.text_color('Update completed.', 'green')
        print _stash.text_color('Please restart Pythonista to ensure changes becoming effective.', 'green')
    except SystemExit:
        print _stash.text_color('Failed to update. Please try again.', 'red')


if __name__ == '__main__':
    main(sys.argv[1:])
