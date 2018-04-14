'''
serach - Searches for packages
versions - Lists all versions for a package
install - Installs the package off pypi
list - Lists currently installed backages.
remove - remove a package installed by pip
update - update a package installed by pip

usage: pip.py [-h] [-n RESULT_COUNT]
              {search,versions,install,list} [package] [version]

positional arguments:
  {search,versions,install,list}
  package
  version

optional arguments:
  -h, --help            show this help message and exit
  -n RESULT_COUNT
'''
import xmlrpclib
from ConfigParser import SafeConfigParser
import requests
import argparse
import tempfile
import re
import os
import sys
import shutil
from types import ModuleType


saved_modules = sys.modules
saved_cwd = os.getcwd()
SITE_PACKAGES = os.path.expanduser('~/Documents/site-packages')

def make_module(new_module, doc="", scope=locals()):
    """
    modified from
    http://dietbuddha.blogspot.com.au/2012/11/python-metaprogramming-dynamic-module.html
    make_module('a.b.c.d', doc="", scope=locals()]) -> <module built-in="built-in" d="d">

    * creates module (and submodules as needed)
    * adds module (and submodules) to sys.modules
    * correctly nests submodules as needed
    * not overwritting existing modules (my modification to the original function)
    """
    module_name = []

    for name in new_module.split('.'):
        m = ModuleType(name, doc)
        parent_module_name = '.'.join(module_name)

        if parent_module_name:
            if parent_module_name not in sys.modules.keys():  # do not overwrite existing modules
                print 'creating parent', parent_module_name
                setattr(sys.modules[parent_module_name], name, m)
        else:
            if m not in scope.keys(): # do not overwrite existing modules
                scope[name] = m

        module_name.append(name)

        name_path = '.'.join(module_name)
        if name_path not in sys.modules.keys(): # do not overwrite existing modules
            print 'Added %s' % name_path
            sys.modules[name_path] = m

    return sys.modules['.'.join(module_name)]

def setup(*args, **kwargs):
    global _stash, pypi
    path = os.path.dirname(__file__)
    name = kwargs['name']
    version =  getattr(kwargs,'version','No version Listed')
    license = getattr(kwargs,'license','No License Listed')
    summary = getattr(kwargs,'description', '')
    #print kwargs['license']
    if 'scripts' in kwargs:
        for script in kwargs['scripts']:

            _stash('mv {folder}/{script} {site}/{script}'.format(site=SITE_PACKAGES,
                                                                     folder=path,
                                                                     script=script))
    if 'packages' in kwargs:
        for script in kwargs['packages']:
            _stash('mv {folder}/{script} {site}/{script}'.format(site=SITE_PACKAGES,
                                                                     folder=path,
                                                                     script=script))
    pypi.pkg_info = {'name':name,'version':version,'license':license,'summary':summary}
    pypi.config.add_module()

    # NOTE: pip installation code here
    # e.g. _stash('mv package_folder ~/Documents/site-packages/package_folder') etc.


class PackageConfigHandler(object):
    def __init__(self):
        self.package_cfg = os.path.expanduser('~/Documents/site-packages/.pypi_packages')
        if not os.path.isfile(self.package_cfg):
            print 'Creating package file'
            f = open(self.package_cfg,'w')
            f.close()
        self.parser = SafeConfigParser()
        self.parser.read(self.package_cfg)

    def save(self):
        with open(self.package_cfg,'w') as f:
            self.parser.write(f)

    def add_module(self):
        tbl = self.parent.pkg_info
        if not self.parser.has_section(tbl['name']):
            self.parser.add_section(tbl['name'])
        if self.pypi_package:
            self.parser.set(tbl['name'],'url','pypi')
        else:
            self.parser.set(tbl['name'],'url',tbl['url'])
        self.parser.set(tbl['name'],'version',tbl['version'])
        self.parser.set(tbl['name'],'summary',tbl['summary'])
        self.save()

    def list_modules(self):
        lst = []
        for module in self.parser.sections():
            lst.append(module)
        return lst


    def module_exists(self,name):
        if self.parser.has_section(name):
            return True
        else:
            return False

    def get_info(self,name):
        if self.parser.has_section(name):
            tbl = {}
            for opt, value in self.parser.items(name):
                tbl[opt] = value
            return tbl

    def remove_module(self,name):
        self.parser.remove_section(name)
        self.save()




class Pypi(object):
    def __init__(self,pkg_name='',url=False,pkg_version='',limit=10):
        self.pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
        self.config = PackageConfigHandler()
        self.url = url
        self.config.pypi_package = False if self.url else True
        self.config.parent = self
        self.pkg_name = pkg_name
        self.pkg_version = pkg_version
        self.limit = limit


        self.filename = ''



    def search(self):
        hits = self.pypi.search({'name': self.pkg_name}, 'and')
        if not hits:
            raise PyPiError('No matches found.')

        hits = sorted(hits, key=lambda pkg: pkg['_pypi_ordering'], reverse=True)
        if len(hits) > self.limit:
            hits = hits[:self.limit]
        for hit in hits:
            print '%s v%s - %s'%(hit['name'],hit['version'],hit['summary'])

    def versions(self,show_hidden=True):
        hits = self.pypi.package_releases(self.pkg_name, show_hidden)

        if not hits:
            raise PyPiError('Package not found.')
        if len(hits) > self.limit:
            hits = hits[:self.limit]
        for hit in hits:
            print '%s - %s'%(self.pkg_name,hit)

    def download(self):
        if self.url:
            print 'External package'
            print 'Not yet implemented.'
        else:
            self.pypi_download()

    def other_download(self):
        #handle non pypi packages
        pass

    def pypi_download(self):
        hits = self.pypi.package_releases(self.pkg_name, True)
        if not hits:
            raise PyPiError('No package found with that name')
        if not self.pkg_version:
            self.pkg_version = hits[0]
        elif not self.pkg_version in hits:
            raise PyPiError('That package version is not available')
        hits = self.pypi.release_urls(self.pkg_name, self.pkg_version)

        if not hits:
            raise PyPiError('No public download links for that version')

        #source = ([x for x in hits if x['packagetype'] == 'sdist'][:1] + [None])[0]
        source = False
        archive_list = ['.zip','.bz2','.gz']
        for hit in hits:
            if any(word in hit['url'] for word in archive_list):
                source = hit
                break

        if not source:
            raise PyPiError('No source-only download links for that version')
        self.url = source['url']
        self.filename = source['filename']
        self.pkg_info = self.pypi.release_data(self.pkg_name, self.pkg_version)
        #tbl={}
        #tbl['url'] = source['url']
        #tbl['filename'] = source['filename']
        #tbl['download_name'] = name
        #tbl['name'] = data['name'].lower()
        #tbl['version'] = data['version']
        #tbl['summary'] = data['summary']
        #print self.__dict__
        self._install()

    def list_modules(self):
        modules = self.config.list_modules()
        for module in modules:
            info = self.config.get_info(module)
            print '%s (%s) - %s' % (module,info['version'],info['summary'])

    def _install(self):
        print 'installing module'
        if '.zip' in self.filename:
            tmp_folder = self.filename[:-4]
            archive_type = 'zip'
        elif '.bz2' in self.filename:
            tmp_folder = self.filename[:-8]
            archive_type = 'bz2'
        else:
            tmp_folder = self.filename[:-7]
            archive_type = 'gz'

        try:
            _stash('echo StaSh pip installing %s'% self.pkg_name)
            _stash('wget %s -o ~/Documents/site-packages/%s' % (self.url,self.filename))
            _stash('cd ~/Documents/site-packages')

            #os.chdir(os.path.expanduser('~/Documents/site-packages'))
            dir_contents = os.listdir(SITE_PACKAGES)

            #un archive file
            if archive_type == 'zip':
                _stash('unzip -d ~/Documents/site-packages/%s ~/Documents/site-packages/%s' % (tmp_folder,self.filename))
            elif archive_type=='gz':
                _stash('tar -xvzf ~/Documents/site-packages/%s' % self.filename)
            elif archive_type=='bz2':
                _stash('tar -xvjf ~/Documents/site-packages/%s' % self.filename)
            else:
                raise PyPiError('No vaild archives found.')


            dir_name =  list(set(os.listdir(SITE_PACKAGES))-set(dir_contents))[0]
            os.chdir(SITE_PACKAGES+'/%s'%dir_name)
            global __file__
            backup_file = __file__

            ##Try to find folders.
            package_name = self.pkg_name.split('.')[0].lower()
            try:
                if os.path.isdir(SITE_PACKAGES+'/%s/%s' % (dir_name,package_name)):
                    _stash('mv ~/Documents/site-packages/{basename}/{name} ~/Documents/site-packages/{name}'.format(basename=dir_name,name=package_name))
                    self.config.add_module()

                elif os.path.isfile(SITE_PACKAGES+'/%s/%s.py' % (dir_name,package_name)):
                    _stash('mv ~/Documents/site-packages/{basename}/{name}.py ~/Documents/site-packages/{name}.py'.format(basename=dir_name,name=package_name))
                    self.config.add_module()
                #check for src
                elif os.path.isdir(SITE_PACKAGES+'/%s/src/%s' % (dir_name,package_name)):
                    _stash('mv ~/Documents/site-packages/{basename}/src/{name} ~/Documents/site-packages/{name}'.format(basename=dir_name,name=package_name))
                    self.config.add_module()
                #Try to run setup
                else:
                    _stash('echo Trying to run setup.py')
                    global setup
                    # Fake the setuptools modules so setup.py can run
                    # fake   from setuptools import setup
                    st = make_module('setuptools')
                    st.__dict__['setup'] = setup  # the custom setup function will perform the installation

                    # more sub-modules to fake
                    # fake    from setuptools.command.test import test
                    test = make_module('setuptools.command.test')
                    test.__dict__['test'] = type('test', (), {})  # dummy class so setup can run

                    dist = make_module('distutils.core')
                    dist.__dict__['setup'] = setup


                    #make_module('distutils.core').__dict__['setup'] = setup
                    __file__ = SITE_PACKAGES+'/%s/setup.py'%dir_name
                    execfile('setup.py')

            except:
                print '*Unable to locate package. Please try manual install.*'
            finally:
                sys.modules = saved_modules
                __file__ = backup_file
                os.chdir(saved_cwd)
                _stash('echo Removing setup files.')
                _stash('rm -r -f ~/Documents/site-packages/%s' % dir_name)
                _stash('rm -r -f ~/Documents/site-packages/%s' % self.filename)

            try:
                __import__(self.pkg_name.lower())
                _stash('echo Package Installed. Import Successful!')
            except:
                _stash('echo Failed import test. Check for dependencies')

        except Exception,e :
            PyPiError('Unable to install package.')

    def remove_module(self,name):
        if self.config.module_exists(name):
            if os.path.isdir(os.path.expanduser('~/Documents/site-packages/%s'%name.lower())):
                shutil.rmtree(os.path.expanduser('~/Documents/site-packages/%s'%name.lower()))
            elif os.path.isfile(os.path.expanduser('~/Documents/site-packages/%s.py'%name.lower())):
                os.remove(os.path.expanduser('~/Documents/site-packages/%s.py'%name.lower()))
            else:
                raise PyPiError('Could not find package.')
            self.config.remove_module(name)
            print 'Package removed.'
        else:
            raise PyPiError('No module by that name. Use pip list for list of installed modules.')

    def update_module(self,name):
        if self.config.module_exists(name):
            current = self.config.get_info(name)
            hit = self.pypi.package_releases(name)[0]
            if not current['version'] == hit:
                print 'Updating %s' % name
                self.remove_module(name)
                self.download()
            else:
                print 'Package upto date.'

        else:
            raise PyPiError('Package not installed. Try pip install [package]')



class PyPiError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command',action='store',choices=('search',
                                                      'versions',
                                                      'install',
                                                      'list',
                                                      'remove',
                                                      'update'))
    ap.add_argument('-n',dest='result_count',default=10, type=int)
    ap.add_argument('-u','--url', dest='url', action='store',default='',help='Not implemented')
    ap.add_argument('package',action='store',nargs='?',default='')
    ap.add_argument('version',action='store',nargs='?', default='')
    args = ap.parse_args()
    pypi = Pypi(pkg_name=args.package,
                limit=args.result_count,
                pkg_version=args.version,
                url=args.url)

    if args.command == 'search':
        pypi.search()
    elif args.command == 'versions':
        pypi.versions()
    elif args.command == 'install':
        pypi.download()
    elif args.command == 'list':
        pypi.list_modules()
    elif args.command ==  'remove':
        pypi.remove_module(args.package)
    elif args.command == 'update':
        pypi.update_module(args.package)


if __name__=='__main__':
    main()
