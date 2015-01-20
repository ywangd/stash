"""
Stash Command Script Manager - managing non-builtin command scripts
"""
import sys
import os
import argparse
import urllib2
import json
import collections
import random
import copy

_stash = globals()['_stash']

try:
    URL_MAIN_INDEX = os.environ['SCM_URL_MAIN_INDEX']
except KeyError:
    URL_MAIN_INDEX = 'https://raw.githubusercontent.com/ywangd/stash-command-script-index/master/index.json'

STASH_ROOT = os.environ['STASH_ROOT']
RECORD_FILE = os.path.join(STASH_ROOT, '.scsm.json')

def refreshable_url(url):
    return '%s?q=%d' % (url, random.randint(0, 9999))

def dict_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = dict_update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


class ScsmException(Exception):
    def __init__(self, message):
        super(ScsmException, self).__init__('scsm: %s' % message)


def get_release_for_version(releases, ver_num=None):
    if ver_num is not None:
        for release in releases:
            if ver_num == release['version']:
                return release
    else:
        ver_digits = (0, 0, 0)
        target_release = None
        try:
            for release in releases:
                this_ver_digits = map(int, release['version'].split('.'))
                if len(this_ver_digits) < 3:
                    this_ver_digits += (0,) * (3 - len(this_ver_digits))
                for i, digit in enumerate(this_ver_digits):
                    if ver_digits[i] < digit:
                        ver_digits = this_ver_digits
                        target_release = release
            return target_release
        except KeyError:
            if releases:
                return releases[0]
    return None


class MergedIndices(object):

    def __init__(self, remote_index_url, record_file,
                 load_remote=True):
        self.remote_index_url = remote_index_url
        self.record_file = record_file
        if load_remote:
            self.remote_index = json.loads(urllib2.urlopen(refreshable_url(remote_index_url)).read())
        else:
            self.remote_index = {'commands': {}}

        if not os.path.exists(record_file):
            with open(record_file, 'w') as outs:
                outs.write('{}')
            self.local_indices = {}
        else:
            with open(record_file) as ins:
                self.local_indices = json.load(ins)
        self.merged_indices = {self.remote_index_url: copy.deepcopy(self.remote_index)}
        dict_update(self.merged_indices,
                    copy.deepcopy(self.local_indices))
        self.merged_index = self.merged_indices[self.remote_index_url]

    def save_local_record(self):
        with open(self.record_file, 'w') as outs:
            json.dump(self.local_indices, outs, indent=1)

    def find_index_url_for_cmd_name(self, cmd_name):
        if cmd_name in self.merged_index['commands'].keys():
            return self.remote_index_url
        else:
            for url in self.merged_indices.keys():
                if cmd_name in self.merged_indices[url]['commands'].keys():
                    return url
        return None

    def list(self, category):
        for url in sorted(self.merged_indices.keys()):
            index = self.merged_indices[url]
            #print '%s (%s)\n' % (index['name'], url)
            commands = index['commands']
            for cmd_name in sorted(commands.keys()):
                info = commands[cmd_name]
                installed = info.get('installed', None)
                if not (category == 'available' and installed) \
                        and not (category == 'installed' and not installed):
                    print '%s (%s)' % (cmd_name,
                                       'installed' if installed else 'available')

    def install(self, cmd_name, ver_num, dest_dir):
        if cmd_name not in self.merged_index['commands'].keys():
            raise ScsmException('%s: command script not found' % cmd_name)

        elif self.merged_index['commands'][cmd_name].get('installed', None):
            raise ScsmException('%s: command script already installed' % cmd_name)

        else:
            meta_url, tag = urllib2.splittag(self.merged_index['commands'][cmd_name]['meta_url'])
            jmsg = json.loads(urllib2.urlopen(refreshable_url(meta_url)).read())
            jmsg = jmsg[tag] if tag else jmsg

            releases = jmsg['releases']

            release = get_release_for_version(releases, ver_num)
            if release is None:
                raise ScsmException('%s: release not found' % cmd_name)

            if 'filetype' not in release:
                if release['url'].endswith('.py'):
                    release['filetype'] = 'SingleFile'
                elif release['url'].endswith('.zip'):
                    release['filetype'] = 'ZippedFiles'
                else:
                    raise ScsmException('%s: unknown filetype' % cmd_name)

            if not dest_dir:
                dest_dir = os.path.join(os.environ['HOME2'], 'bin')

            dest_dir = os.path.abspath(dest_dir)
            if not os.path.exists(dest_dir) or not os.path.isdir(dest_dir):
                _stash('mkdir %s' % dest_dir)

            filetype = release['filetype']
            files_installed = []

            if filetype == 'SingleFile':
                _stash('cd %s' % dest_dir)
                filename = cmd_name if cmd_name.endswith('.py') else (cmd_name + '.py')
                _stash('wget %s -o %s' % (release['url'], filename))
                files_installed.append(filename)

            elif filetype == 'ZippedFiles':
                _stash('cd $TMPDIR')
                _stash('wget %s -o files.zip' % release['url'])
                _stash('unzip files.zip -v -d %s > files.log' % dest_dir)
                with open(os.path.join(os.environ['TMPDIR'], 'files.log')) as ins:
                    lines = [line.strip() for line in ins.readlines() if line.strip() != '']
                    for line in lines:
                        f = os.path.relpath(line, dest_dir)
                        if f != '.':
                            files_installed.append(f)
                _stash('rm files.zip files.log')
            else:
                raise ScsmException('%s: unknown filetype' % cmd_name)

            installed = {
                'version': release['version'],
                'dest_dir': dest_dir,
                'filetype': release['filetype'],
                'files': files_installed
            }

            if self.remote_index_url not in self.local_indices:
                self.local_indices[self.remote_index_url] = {'commands': {}}

            self.local_indices[self.remote_index_url]['commands'][cmd_name] = {'installed': installed}
            self.save_local_record()
            print '%s installed' % cmd_name

    def remove(self, cmd_name):
        url = self.find_index_url_for_cmd_name(cmd_name)

        if url is None:
            raise ScsmException('%s: command script not installed' % cmd_name)

        else:
            merged_index = self.merged_indices[url]
            info = merged_index['commands'][cmd_name]
            _stash('cd %s' % info['installed']['dest_dir'])
            if info['installed']['filetype'] == 'SingleFile':
                for f in info['installed']['files']:
                    _stash('rm %s' % f)
            elif info['installed']['filetype'] == 'ZippedFiles':
                removed_dirs = set()
                for f in info['installed']['files']:
                    this_dir = os.path.dirname(f)
                    if this_dir != '' and this_dir not in removed_dirs:
                        _stash('rm -r %s' % this_dir)
                        removed_dirs.add(this_dir)
                    else:
                        _stash('rm %s' % f)

            self.local_indices[self.remote_index_url]['commands'].pop(cmd_name)
            self.save_local_record()
            print '%s removed' % cmd_name

    def info(self, cmd_name):
        url = self.find_index_url_for_cmd_name(cmd_name)

        if url is None:
            raise ScsmException('%s: command script not installed' % cmd_name)

        else:
            merged_index = self.merged_indices[url]
            meta_url, tag = urllib2.splittag(merged_index['commands'][cmd_name]['meta_url'])
            jmsg = json.loads(urllib2.urlopen(refreshable_url(meta_url)).read())
            jmsg = jmsg[tag] if tag else jmsg

            author = jmsg.get('author', '')
            email = jmsg.get('email', '')
            website = jmsg.get('website', '')
            description = jmsg.get('description', 'N/A')

            versions = []
            for release in jmsg.get('releases', []):
                versions.append(release.get('version', 'N/A'))

            print 'Name: %s' % cmd_name
            print 'Description: %s' % description
            if website:
                print 'Website: %s' % website
            if author:
                print 'Author: %s' % author
            if email:
                print 'Email: %s' % email
            print 'Versions available:'
            for v in versions:
                print '    %s' % v

            info = merged_index['commands'][cmd_name]
            installed = info.get('installed', None)
            if installed:
                print '\nVersion %s installed at:' % installed['version']
                print _stash.libcore.collapseuser(installed['dest_dir'])
                for f in installed['files']:
                    print '  %s' % f


def main(args):
    ap = argparse.ArgumentParser(description='StaSh Command Manager')
    subparsers = ap.add_subparsers(dest='sub_command', help='sub-command to perform')
    list_parser = subparsers.add_parser('list', help='List all commands')
    list_parser.add_argument('category',
                             nargs='?',
                             default='all',
                             choices=('all',
                                      'installed',
                                      'available'),
                             help='category to list')

    install_parser = subparsers.add_parser('install',
                                           help='Install a command')
    install_parser.add_argument('command',
                                help='command to install')
    install_parser.add_argument('version',
                                nargs='?',
                                help='version of the command to install')
    install_parser.add_argument('-d', '--dest-dir',
                                help='Destination folder to install')

    remove_parser = subparsers.add_parser('remove',
                                          help='Remove a command')
    remove_parser.add_argument('command',
                               help='command to remove')

    info_parser = subparsers.add_parser('info',
                                        help='Show detailed information of a command')
    info_parser.add_argument('command',
                             help='command to show info')

    ns = ap.parse_args(args)

    try:
        if ns.sub_command == 'list':
            load_remote = False if ns.category == 'installed' else True
            merged_indices = MergedIndices(URL_MAIN_INDEX, RECORD_FILE, load_remote=load_remote)
            merged_indices.list(ns.category)

        elif ns.sub_command == 'install':
            merged_indices = MergedIndices(URL_MAIN_INDEX, RECORD_FILE)
            merged_indices.install(ns.command, ns.version, ns.dest_dir)

        elif ns.sub_command == 'remove':
            merged_indices = MergedIndices(URL_MAIN_INDEX, RECORD_FILE, load_remote=False)
            merged_indices.remove(ns.command)

        elif ns.sub_command == 'info':
            merged_indices = MergedIndices(URL_MAIN_INDEX, RECORD_FILE)
            merged_indices.info(ns.command)

    except ScsmException as e:
        print e.message
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])

