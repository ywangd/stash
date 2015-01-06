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
import argparse
import tempfile
import re
import os
import sys
import shutil

package_file = os.path.expanduser('~/Documents/site-packages/.pypi_packages')

class PackageConfigHandler(object):
    def __init__(self):
        if not os.path.isfile(package_file):
            print 'Creating package file'
            f = open(package_file,'w')
            f.close()
        self.parser = SafeConfigParser()
        self.parser.read(package_file)
     
    def add_module(self,name,ver,summary):
        if not self.parser.has_section(name):
            self.parser.add_section(name)
            
        self.parser.set(name,'version',ver)
        self.parser.set(name,'summary',summary)
    
        self.save_config()
        
    def save_config(self):
        with open(package_file,'w') as f:
            self.parser.write(f)
        
    def list_modules(self):
        for module in self.parser.sections():
            print '%s (%s) - %s' % (module,self.parser.get(module,'version'),self.parser.get(module,'summary'))
    
    def module_exists(self,name):
        if self.parser.has_section(name):
            return True
        else:
            return False
            
    def remove_module(self,name):
        self.parser.remove_section(name)
        self.save_config()
        
    def update_module(self):
        pass
        
class Pypi(object):
    def __init__(self):
        self.pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
        self.handler = PackageConfigHandler()
        
        
    def search(self,search_str,limit=10):
        hits = self.pypi.search({'name': search_str}, 'and')
        if not hits:
            print 'No matches found.'
            return
        hits = sorted(hits, key=lambda pkg: pkg['_pypi_ordering'], reverse=True)
        if len(hits) > limit:
            hits = hits[:limit]
        for hit in hits:
            print '%s v%s - %s'%(hit['name'],hit['version'],hit['summary'])
        
    def versions(self,name,limit=10,show_hidden=True):
        hits = self.pypi.package_releases(name, show_hidden)
    
        if not hits:
            print 'Package not found.'
            return 
        if len(hits) > limit:
            hits = hits[:limit]
        for hit in hits:
            print '%s - %s'%(name,hit)
        
    def download(self,name,ver=''):
        hits = self.pypi.package_releases(name, True)
        if not hits:
            raise PyPiError('No package found with that name')
        if not ver:
            ver = hits[0]
        elif not ver in hits:
            raise PyPiError('That package version is not available')
        hits = self.pypi.release_urls(name, ver)
        
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
        data = self.pypi.release_data(name, ver)
        
        tbl={}
        tbl['url'] = source['url']
        tbl['filename'] = source['filename']
        tbl['name'] = data['name'].lower()
        tbl['version'] = data['version']
        tbl['summary'] = data['summary']
        self._install(tbl)     
        
    def list_modules(self):
        self.handler.list_modules()
        
    def _install(self,data):
        if '.zip' in data['filename']:
            tmp_folder = data['filename'][:-4]
        elif '.bz2' in data['filename']:
            tmp_folder = data['filename'][:-8]
        else:
            tmp_folder = data['filename'][:-7]
        for n,i in data.items():
            print '%s - %s ' % (n,i)
        
        try:
            _stash('echo StaSh pip installing %s'% data['name'])
            _stash('wget %s -o ~/Documents/site-packages/%s' % (data['url'],data['filename']))
            _stash('cd ~/Documents/site-packages')
            if '.zip' in data['filename']:
                _stash('unzip -d ~/Documents/site-packages/%s ~/Documents/site-packages/%s' % (tmp_folder,data['filename']))
            elif '.gz' in data['filename']:
                
                _stash('tar -xvzf ~/Documents/site-packages/%s' % data['filename'])
            elif '.bz2' in data['filename']:
                _stash('tar -xvjf ~/Documents/site-packages/%s' % data['filename'])
            else:
                raise PyPiError('No vaild archives found.')
                
            try:
                if os.path.isdir(os.path.expanduser('~/Documents/site-packages/%s/%s' % (tmp_folder,data['name']))):
                    _stash('mv ~/Documents/site-packages/{basename}/{name} ~/Documents/site-packages/{name}'.format(basename=tmp_folder,name=data['name']))
                elif os.path.isfile(os.path.expanduser('~/Documents/site-packages/%s/%s.py' % (tmp_folder,data['name']))):
                    _stash('mv ~/Documents/site-packages/{basename}/{name}.py ~/Documents/site-packages/{name}.py'.format(basename=tmp_folder,name=data['name']))
                else:
                    raise PyPiError('Unable to move package files. Package not Installed.')
            except PyPiError,e:
                print e.value
                sys.exit(1)
            finally:
                _stash('echo Removing setup files.')
                _stash('rm -r -f ~/Documents/site-packages/%s' % tmp_folder)
                _stash('rm -r -f ~/Documents/site-packages/%s' % data['filename'])
    
            self.handler.add_module(data['name'],data['version'],data['summary'])
        
            try:
                __import__(data['name'])
                _stash('echo Package Installed. Import Successful!')
            except:
                _stash('echo Failed import test. Check for dependencies')
            
        except Exception,e :
            PyPiError('Unable to install package.')
            
    def remove_module(self,name):
        if self.handler.module_exists(name):
            if os.path.isdir(os.path.expanduser('~/Documents/site-packages/%s'%name)):
                shutil.rmtree(os.path.expanduser('~/Documents/site-packages/%s'%name))
            elif os.path.isfile(os.path.expanduser('~/Documents/site-packages/%s.py'%name)):
                os.remove(os.path.expanduser('~/Documents/site-packages/%s.py'%name))
            else:
                raise PyPiError('Could not find package.')
            self.handler.remove_module(name)
            print 'Package removed.'
        else:
            print 'No module by that name. Use pip list for list of installed modules.'
            
    def update_module(self,name):
        if self.handler.module_exists(name):
            self.remove_module(name)
            self.download(name)
        else:
            raise PyPiError('Package not installed. Try pip install [package]')
        

class PyPiError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
        
  

if __name__=='__main__':
    
    ap = argparse.ArgumentParser()
    ap.add_argument('command',action='store',choices=('search','versions','install','list','remove','update'))
    ap.add_argument('-n',dest='result_count',default=10, type=int)
    ap.add_argument('package',action='store',nargs='?')
    ap.add_argument('version',action='store',nargs='?', default='')
    args = ap.parse_args()
    pypi = Pypi()
    if args.command == 'search':
        pypi.search(args.package,args.result_count)
    elif args.command == 'versions':
        pypi.versions(args.package, args.result_count)
    elif args.command == 'install':
        pypi.download(args.package, args.version)
    elif args.command == 'list':
        pypi.list_modules()
    elif args.command ==  'remove':
        pypi.remove_module(args.package)
    elif args.command == 'update':
        pypi.update_module(args.package)

 

