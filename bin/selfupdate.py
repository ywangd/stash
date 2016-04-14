# coding=utf-8
"""
Selfupdate StaSh from the GitHub repo.

Usage: selfupdate.py [-n] [-f] [branch]

       branch         default to master

       -n, --check    check for update only
       -f, --force    update without checking for new version
"""
from __future__ import unicode_literals
import os
import sys
import requests
from random import randint
from argparse import ArgumentParser

_stash = globals()['_stash']

URL_BASE = 'https://raw.githubusercontent.com/ywangd/stash'


class UpdateError(Exception):
    pass


def get_remote_version(branch):
    """
    Get the version string for the given branch from the remote repo
    :param branch:
    :return:
    """
    import ast

    url = '%s/%s/stash.py?q=%s' % (URL_BASE, branch, randint(1, 999999))

    try:
        lines = requests.get(url).text.splitlines()
    except:
        raise UpdateError('Network error')

    for line in lines:
        if line.startswith('__version__'):
            remote_version = ast.literal_eval(line.split('=')[1].strip())
            return remote_version

    raise UpdateError('Remote version cannot be decided')


def main(args):

    from distutils.version import StrictVersion

    ap = ArgumentParser()
    ap.add_argument('branch', nargs='?', help='the branch to update to')
    ap.add_argument('-n', '--check', action='store_true', help='check for update only')
    ap.add_argument('-f', '--force', action='store_true', help='update without checking for new version')
    ns = ap.parse_args(args)

    if ns.branch is not None:
        SELFUPDATE_BRANCH = ns.branch
    else:
        SELFUPDATE_BRANCH = os.environ.get('SELFUPDATE_BRANCH', 'master')

    print(_stash.text_style('Running selfupdate ...',
                            {'color': 'yellow', 'traits': ['bold']}))
    print(u'%s: %s' % (_stash.text_bold('Branch'), SELFUPDATE_BRANCH))

    has_update = True
    # Check for update if it is not forced updating
    if not ns.force:
        local_version = globals()['_stash'].__version__
        try:
            print('Checking for new version ...')
            remote_version = get_remote_version(SELFUPDATE_BRANCH)

            if StrictVersion(remote_version) > StrictVersion(local_version):
                print('New version available: %s' % remote_version)
            else:
                has_update = False
                print('Already at latest version')

        except UpdateError as e:
            has_update = False  # do not update in case of errors
            print(_stash.text_color('Error: {}'.format(e), 'red'))

    # Perform update if new version is available and not just checking only
    if not ns.check and has_update:

        url = '%s/%s/getstash.py' % (URL_BASE, SELFUPDATE_BRANCH)
        print(u'%s: %s' % (_stash.text_bold('Url'),
                           _stash.text_style(url, {'color': 'blue', 'traits': ['underline']})))

        try:
            exec(requests.get(
                '%s/%s/getstash.py?q=%s' % (URL_BASE,
                                            SELFUPDATE_BRANCH,
                                            randint(1, 999999))
            ).text, {'_IS_UPDATE': True, '_br': SELFUPDATE_BRANCH})
            print(_stash.text_color('Update completed.', 'green'))
            print(_stash.text_color('Please restart Pythonista to ensure changes becoming effective.', 'green'))

        except SystemExit:
            print(_stash.text_color('Failed to update. Please try again.', 'red'))


if __name__ == '__main__':
    main(sys.argv[1:])
