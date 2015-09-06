# coding: utf-8
"""
Selfupdate StaSh from the GitHub repo.

Usage: selfupdate.py [branch]

       branch: default to master
"""
import os
import sys

_stash = globals()['_stash']

try:
    SELFUPDATE_BRANCH = sys.argv[1]
except IndexError:
    # SELFUPDATE_BRANCH = os.environ.get('SELFUPDATE_BRANCH', 'master')
    SELFUPDATE_BRANCH = 'beta16'  # default to the beta branch for now

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
    ).read() in {'_IS_UPDATE': True, 'branch': SELFUPDATE_BRANCH}
    print _stash.text_color('Update completed.', 'green')
    print _stash.text_color('Please restart StaSh to ensure changes becoming effective.', 'green')
except SystemExit:
    print _stash.text_color('Failed to update. Please try again.', 'red')
