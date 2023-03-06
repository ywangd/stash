# -*- coding: utf-8 -*-
"""
Install and manage python packages

usage: pip.py [-h] [--verbose] sub-command ...

optional arguments:
  -h, --help    show this help message and exit
  --verbose     be more chatty

List of sub-commands:
    sub-command     "pip sub-command -h" for more help on a sub-command
        list        list packages installed
        install     install packages
        download    download packages
        search      search with the given word fragment
        versions    find versions available for the given package
        uninstall   uninstall packages
        update      update an installed package
"""
from __future__ import print_function
import sys
import os
import ast
import shutil
import types
import contextlib
import requests
import operator
import traceback
import platform
import json

import six
from distutils.util import convert_path
from fnmatch import fnmatchcase
# noinspection PyUnresolvedReferences
from six.moves import filterfalse

from stashutils.extensions import create_command
from stashutils.wheels import Wheel, wheel_is_compatible

_stash = globals()['_stash']
VersionSpecifier = _stash.libversion.VersionSpecifier  # alias for readability
SITE_PACKAGES_FOLDER = _stash.libdist.SITE_PACKAGES_FOLDER
OLD_SITE_PACKAGES_FOLDER = _stash.libdist.SITE_PACKAGES_FOLDER_6
BUNDLED_MODULES = _stash.libdist.BUNDLED_MODULES
BLOCKLIST_PATH = os.path.join(os.path.expandvars("$STASH_ROOT"), "data", "pip_blocklist.json")
PIP_INDEX_FILE = os.path.join(SITE_PACKAGES_FOLDER,'pip_index.json')
PIP_INFO_FILE = os.path.join(SITE_PACKAGES_FOLDER, '.package_info', '%s.json')

# Some packages use wrong name for their dependencies
PACKAGE_NAME_FIXER = {
    'lazy_object_proxy': 'lazy-object-proxy',
}

NO_OVERWRITE = False

# Utility constants
FLAG_DIST_ALLOW_SRC = 1
FLAG_DIST_ALLOW_WHL = 2
FLAG_DIST_PREFER_SRC = 4
FLAG_DIST_PREFER_WHL = 8
FLAG_IGNORE_BLOCKLIST = 16
DEFAULT_FLAGS = FLAG_DIST_ALLOW_SRC | FLAG_DIST_ALLOW_WHL | FLAG_DIST_PREFER_WHL


def _setup_stub_(*args, **kwargs):
    setuptools = sys.modules['setuptools']
    setuptools._setup_params_ = (args, kwargs)


class PipError(Exception):
    """
    Baseclass for pip related errors.
    """
    pass


class PackageAlreadyInstalled(PipError):
    """
    Error raised when a package is already installed.
    """
    pass


class PackageBlocklisted(PipError):
    """
    Error raised when a package is fataly blocklisted
    :param pkg_name: name of blocklisted package
    :type pkg_name: str
    :param reason: reason for blocklisting
    :type reason: str
    """
    def __init__(self, pkg_name, reason):
        s = "Package '{}' blocklisted. Reason: {}".format(pkg_name, reason)
        PipError.__init__(self, s)


class OmniClass(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return OmniClass()

    def __getattr__(self, item):
        return OmniClass()

    def __getitem__(self, item):
        return OmniClass()

    def __mro_entries__(self, bases):
        return (self.__class__, )


class PackageFinder(object):
    """
    This class is copied from setuptools
    """

    @classmethod
    def find(cls, where='.', exclude=(), include=('*', )):
        """Return a list all Python packages found within directory 'where'

        'where' should be supplied as a "cross-platform" (i.e. URL-style)
        path; it will be converted to the appropriate local path syntax.
        'exclude' is a sequence of package names to exclude; '*' can be used
        as a wildcard in the names, such that 'foo.*' will exclude all
        subpackages of 'foo' (but not 'foo' itself).

        'include' is a sequence of package names to include.  If it's
        specified, only the named packages will be included.  If it's not
        specified, all found packages will be included.  'include' can contain
        shell style wildcard patterns just like 'exclude'.

        The list of included packages is built up first and then any
        explicitly excluded packages are removed from it.
        """
        out = cls._find_packages_iter(convert_path(where))
        out = cls.require_parents(out)
        includes = cls._build_filter(*include)
        excludes = cls._build_filter('ez_setup', '*__pycache__', *exclude)
        out = filter(includes, out)
        out = filterfalse(excludes, out)
        return list(out)

    @staticmethod
    def require_parents(packages):
        """
        Exclude any apparent package that apparently doesn't include its
        parent.

        For example, exclude 'foo.bar' if 'foo' is not present.
        """
        found = []
        for pkg in packages:
            base, sep, child = pkg.rpartition('.')
            if base and base not in found:
                continue
            found.append(pkg)
            yield pkg

    @staticmethod
    def _candidate_dirs(base_path):
        """
        Return all dirs in base_path that might be packages.
        """
        has_dot = lambda name: '.' in name
        for root, dirs, files in os.walk(base_path, followlinks=True):
            # Exclude directories that contain a period, as they cannot be
            #  packages. Mutate the list to avoid traversal.
            dirs[:] = filterfalse(has_dot, dirs)
            for dir in dirs:
                yield os.path.relpath(os.path.join(root, dir), base_path)

    @classmethod
    def _find_packages_iter(cls, base_path):
        candidates = cls._candidate_dirs(base_path)
        return (
            path.replace(os.path.sep,
                         '.') for path in candidates if cls._looks_like_package(os.path.join(base_path,
                                                                                             path))
        )

    @staticmethod
    def _looks_like_package(path):
        return os.path.isfile(os.path.join(path, '__init__.py'))

    @staticmethod
    def _build_filter(*patterns):
        """
        Given a list of patterns, return a callable that will be true only if
        the input matches one of the patterns.
        """
        return lambda name: any(fnmatchcase(name, pat=pat) for pat in patterns)


class SetuptoolsStub(types.ModuleType):
    """
    Approximate setuptools by providing and empty module and objects
    """

    def __init__(self, *args, **kwargs):
        super(SetuptoolsStub, self).__init__(*args, **kwargs)
        self._installed_requirements_ = []

    def __getattr__(self, item):
        self_name = object.__getattribute__(self, '__name__')
        # print('{} getting {!r}'.format(self_name, item))
        if self_name == 'setuptools':
            if item == '_setup_params_':
                return (), {}
            elif item == 'find_packages':
                return PackageFinder.find
        return OmniClass()

def get_requires(package, index_file=PIP_INDEX_FILE):
    """
    get require of the package
    :param package: package name
    :type package: str
    :return: a list of requires package
    :rtype: list
    """
    if os.path.exists(index_file):
        with open(index_file) as f:
            index=json.load(f)
            try:
                return index[package]
            except KeyError:# no such package in index file
                raise PipError("Cannot find packages in index file. Try to using 'pip dev update-index' to update index file")

    else:
        raise PipError("Cannot find index file. Try to using 'pip dev update-index' to update index file")

def get_req_by(package, index_file=PIP_INDEX_FILE):
    """
    get the packages that require this package
    :param package: package name
    :type package: str
    :return: a list of packages that require this package
    :rtype: list
    """
    if os.path.exists(index_file):

        with open(index_file) as f:
            index=json.load(f)
            required_by=[]
            for pkg, req in index.items():
                if package in req:
                    required_by.append(pkg)
    else:

        raise PipError("Cannot find index file. Try to using 'pip dev update-index' to update index file")

    return required_by 





def print_info(package, pip_info_file=PIP_INFO_FILE, site_packages=SITE_PACKAGES_FOLDER):
    info_file = pip_info_file % package
    if os.path.exists(info_file):
        with open(info_file) as f:
            info = json.load(f)
        print('Name: {}'.format(info['name']))
        print('Version: {}'.format(info['version']))
        print('Summary: {}'.format(info['summary']))
        print('Home-page: {}'.format(info['project_urls']['Homepage']))
        print('Author: {}'.format(info['author']))
        print('Author-email: {}'.format(info['author_email']))
        print('License: {}'.format(info['license']))
        print('Location: {}'.format(site_packages))
       
        requires = get_requires(package)
        required_by = get_req_by(package)
        print('requires: {}'.format(', '.join(requires)))
        print('required-by: {}'.format(', '.join(required_by)))
    else: #no info_file
        print(_stash.text_color('Package not found: {}'.format(package), 'yellow'))
        


def download_info(pkg_name, pip_info_file=PIP_INFO_FILE, site_packages=SITE_PACKAGES_FOLDER):
    info_file = pip_info_file % pkg_name
    r=requests.get('https://pypi.python.org/pypi/{}/json'.format(pkg_name))
    info=r.json()['info']
    info_folder = os.path.split(info_file)[0]
    if not os.path.exists(info_folder):
        os.mkdir(info_folder)
    with open(info_file, 'w') as f:
        json.dump(info, f)
    update_req_index()

def update_req_index(pip_info_file=PIP_INFO_FILE, site_packages=SITE_PACKAGES_FOLDER, index_file=PIP_INDEX_FILE):
    '''
    update package requires index file 
    '''
    repository = get_repository('pypi', site_packages=site_packages)
    info_list = repository.list()

    req_index={} # a dict of {package:requires_list}  type:dict of {str:list of str}
    for package, info in info_list:
        info_file = pip_info_file % package
        if os.path.exists(info_file):
            # load info
            with open(info_file) as f:
                info=json.load(f)
            # filte requires 
            requires = []
            try:
                for req in info['requires_dist']:
                    if ';' not in req:
                        #Remove package version
                        requires.append(req.split(' ')[0])
            except TypeError:# some package may have no require
                pass
            req_index[package]=requires

        else: # info file not exists
            print(_stash.text_color('Info file of Package {} not found'.format(package), 'yellow'))


    with open(index_file, 'w') as f:
        json.dump(req_index,f)

def fake_module(new_module):
    """
    Created dummy empty modules
    :param new_module: The name of a module to be faked
    """
    module_names = []
    for name in new_module.split('.'):
        parent_name = '.'.join(module_names)
        module_names.append(name)
        full_name = '.'.join(module_names)

        m = SetuptoolsStub(full_name, '')

        if parent_name != '':
            parent_module = sys.modules[parent_name]
            if name not in parent_module.__dict__:  # cannot use getattr
                # print('setting {}'.format(name))
                setattr(sys.modules[parent_name], name, m)

        if full_name not in list(sys.modules.keys()):
            sys.modules[full_name] = m


def fake_setuptools_modules():
    """
    Created a bunch of stub setuptools modules
    """
    setuptools_modules = [
        'setuptools',
        'setuptools.command',
        'setuptools.command.alias',
        'setuptools.command.bdist_egg',
        'setuptools.command.bdist_rpm',
        'setuptools.command.bdist_wininst',
        'setuptools.command.build_ext',
        'setuptools.command.build_py',
        'setuptools.command.develop',
        'setuptools.command.easy_install',
        'setuptools.command.egg_info',
        'setuptools.command.install',
        'setuptools.depends.install_egg_info',
        'setuptools.command.install_lib',
        'setuptools.command.install_scripts',
        'setuptools.command.register',
        'setuptools.command.rotate',
        'setuptools.command.saveopts',
        'setuptools.command.sdist',
        'setuptools.command.setopt',
        'setuptools.command.test',
        'setuptools.command.upload',
        'setuptools.command.upload_docs',
        'setuptools.extern',
        'setuptools.dist',
        'setuptools.extension',
        'setuptools.launch',
        'setuptools.lib2to3_ex',
        'setuptools.msvc9_support',
        'setuptools.package_index',
        'setuptools.py26compat',
        'setuptools.py27compat',
        'setuptools.py31compat',
        'setuptools.sandbox',
        'setuptools.site-patch',
        'setuptools.ssl_support',
        'setuptools.unicode_utils',
        'setuptools.utils',
        'setuptools.version',
        'setuptools.windows_support',
        # 'pkg_resources',
        # 'pkg_resources.extern',
    ]

    for m in setuptools_modules:
        fake_module(m)

    # First import importable distutils
    import distutils.command
    import distutils.core
    import distutils.util
    distutils_command_modules = [
        'distutils.command.bdist'
        'distutils.command.bdist_dumb',
        'distutils.command.bdist_msi',
        'distutils.command.bdist_rpm',
        'distutils.command.bdist_wininst',
        'distutils.command.build',
        'distutils.command.build_clib',
        'distutils.command.build_ext',
        'distutils.command.build_py',
        'distutils.command.build_scripts',
    ]
    for m in distutils_command_modules:
        fake_module(m)
    sys.modules['distutils.util'].get_platform = OmniClass()
    # fix for new problem in issue 169
    sys.modules['distutils.command.build_ext'].sub_commands = []
    sys.modules['setuptools.command.build_ext'].sub_commands = []


def ensure_pkg_resources():
    try:
        import pkg_resources
    except ImportError:
        try:
            print('Approximating pkg_resources ...')
            GitHubRepository().install('ywangd/pkg_resources', None)
        except:  # silently fail as it may not be important or necessary
            pass


@contextlib.contextmanager
def save_current_sys_modules():
    """
    Save the current sys modules and restore them when processing is over
    """
    # saved_sys_modules = dict(sys.modules)
    save_setuptools = {}
    for name in sorted(sys.modules.keys()):
        if name == 'setuptools' or name.startswith('setuptools.'):
            save_setuptools[name] = sys.modules.pop(name)

    yield

    # sys.modules = saved_sys_modules
    for name in sorted(sys.modules.keys()):
        if name == 'setuptools' or name.startswith('setuptools.'):
            sys.modules.pop(name)
    for k, v in save_setuptools.items():
        sys.modules[k] = v


# warning: the ConfigParser may refer to a different class depening on the used py version
# though I believe that pip does not use interpolation, so we *should* be safe
# noinspection PyUnresolvedReferences
from six.moves.configparser import ConfigParser, NoSectionError


class CIConfigParer(ConfigParser):
    """
    This config parser is case insensitive for section names so that
    the behaviour matches pypi queries.
    """

    def _get_section_name(self, name):
        for section_name in self.sections():
            if section_name.lower() == name.lower():
                return section_name
        else:
            raise NoSectionError(name)

    def has_section(self, name):
        names = [n.lower() for n in self.sections()]
        return name.lower() in names

    def has_option(self, name, option_name):
        section_name = self._get_section_name(name)
        return ConfigParser.has_option(self, section_name, option_name)

    def items(self, name):
        section_name = self._get_section_name(name)
        return ConfigParser.items(self, section_name)

    def get(self, name, option_name, *args, **kwargs):
        section_name = self._get_section_name(name)
        return ConfigParser.get(self, section_name, option_name, *args, **kwargs)

    def set(self, name, option_name, value):
        section_name = self._get_section_name(name)
        return ConfigParser.set(self, section_name, option_name, value.replace('%', '%%'))

    def remove_section(self, name):
        section_name = self._get_section_name(name)
        return ConfigParser.remove_section(self, section_name)


class PackageConfigHandler(object):
    """
    Manager class for packages files for tracking installation of modules
    """

    def __init__(self, site_packages=SITE_PACKAGES_FOLDER, verbose=False):
        self.verbose = verbose
        self.site_packages = site_packages
        self.package_cfg = os.path.join(site_packages, '.pypi_packages')
        if not os.path.isfile(self.package_cfg):
            if self.verbose:
                print('Creating package file...')
            with open(self.package_cfg, 'w') as outs:
                outs.close()
        self.parser = CIConfigParer()
        self.parser.read(self.package_cfg)

    def save(self):
        with open(self.package_cfg, 'w') as outs:
            self.parser.write(outs)

    def add_module(self, pkg_info):
        """

        :param pkg_info: A dict that has name, url, version, summary
        :return:
        """
        if not self.parser.has_section(pkg_info['name']):
            self.parser.add_section(pkg_info['name'])
        self.parser.set(pkg_info['name'], 'url', pkg_info['url'])
        self.parser.set(pkg_info['name'], 'version', pkg_info['version'])
        self.parser.set(pkg_info['name'], 'summary', pkg_info['summary'])
        self.parser.set(pkg_info['name'], 'files', pkg_info['files'])
        self.parser.set(pkg_info['name'], 'dependency', pkg_info['dependency'])
        self.save()

    def list_modules(self):
        return [module for module in self.parser.sections()]

    def module_exists(self, name):
        return self.parser.has_section(name)

    def get_info(self, name):
        if self.parser.has_section(name):
            tbl = {}
            for opt, value in self.parser.items(name):
                tbl[opt] = value
            return tbl

    def remove_module(self, name):
        self.parser.remove_section(name)
        self.save()

    def get_files_installed(self, section_name):
        if self.parser.has_option(section_name, 'files'):
            files = self.parser.get(section_name, 'files').strip()
            return files.split(',')
        else:
            return None

    def get_dependencies(self, section_name):
        if self.parser.has_option(section_name, 'dependency'):
            dependencies = self.parser.get(section_name, 'dependency').strip()
            return set(dependencies.split(',')) if dependencies != '' else set()
        else:
            return None

    def get_all_dependencies(self, exclude_module=()):
        all_dependencies = set()
        for section_name in self.parser.sections():
            if section_name not in exclude_module and self.parser.has_option(section_name, 'dependency'):
                dependencies = self.parser.get(section_name, 'dependency').strip()
                if dependencies != '':
                    for dep in dependencies.split(','):
                        all_dependencies.add(dep)
        return all_dependencies


# noinspection PyPep8Naming,PyProtectedMember
class ArchiveFileInstaller(object):
    """
    Package Installer for archive files, e.g. zip, gz, bz2
    """

    class SetupTransformer(ast.NodeTransformer):
        """
        Analyze and Transform AST of a setup file.
        1. Create empty modules for any setuptools imports (if it is not already covered)
        2. replace setup calls with a stub one to get values of its arguments
        """

        def visit_Import(self, node):
            for idx, alias in enumerate(node.names):
                if alias.name.startswith('setuptools'):
                    fake_module(alias.name)
            return node

        def vist_ImportFrom(self, node):
            if node.module.startswith('setuptools'):
                fake_module(node.module)
            return node

        def visit_Call(self, node):
            func_name = self._get_possible_setup_name(node)
            if func_name is not None and \
            (func_name == 'setup' or func_name.endswith('.setup')):
                node.func = ast.copy_location(ast.Name('_setup_stub_', ast.Load()), node.func)
            return node

        def _get_possible_setup_name(self, node):
            names = []
            func = node.func
            while isinstance(func, ast.Attribute):
                names.append(func.attr)
                func = func.value

            if isinstance(func, ast.Name):
                names.append(func.id)
                return '.'.join(reversed(names))
            else:
                return None

    def __init__(self, site_packages=SITE_PACKAGES_FOLDER, verbose=False):
        self.site_packages = site_packages
        self.verbose = verbose

    def run(self, pkg_name, archive_filename, extras=[]):
        """
        Main method for Installer to do its job.
        :param pkg_name: name of package
        :type pkg_name: str
        :param archive_filename: path to archive
        :type param: str
        :param extras: extras to install
        :type extras: list of str
        :return: tuple of (files installed, dependencies)
        :rtype: tuple of (list of str, list of str)
        """

        extracted_folder = self._unzip(pkg_name, archive_filename)
        try:
            # locate the setup file
            src_dir = os.path.join(extracted_folder, os.listdir(extracted_folder)[0])
            setup_filename = os.path.join(src_dir, 'setup.py')

            try:
                print('Running setup file ...')
                return self._run_setup_file(setup_filename, extras=extras)

            except Exception as e:
                print('{!r}'.format(e))
                print('Failed to run setup.py')
                if self.verbose:
                    # print traceback
                    print("")
                    traceback.print_exc()
                    print("")
                print('Fall back to directory guessing ...')

                pkg_name = pkg_name.lower().replace('-', '_')

                if os.path.isdir(os.path.join(src_dir, pkg_name)):
                    ArchiveFileInstaller._safe_move(
                        os.path.join(src_dir,
                                     pkg_name),
                        os.path.join(self.site_packages,
                                     pkg_name)
                    )
                    return [os.path.join(self.site_packages, pkg_name)], []

                elif os.path.isfile(os.path.join(src_dir, pkg_name + '.py')):
                    ArchiveFileInstaller._safe_move(
                        os.path.join(src_dir,
                                     pkg_name + '.py'),
                        os.path.join(self.site_packages,
                                     pkg_name + '.py')
                    )
                    return [os.path.join(self.site_packages, pkg_name + '.py')], []

                elif os.path.isdir(os.path.join(src_dir, 'src', pkg_name)):
                    ArchiveFileInstaller._safe_move(
                        os.path.join(src_dir,
                                     'src',
                                     pkg_name),
                        os.path.join(self.site_packages,
                                     pkg_name)
                    )
                    return [os.path.join(self.site_packages, pkg_name)], []

                else:
                    raise PipError('Cannot locate packages. Manual installation required.')

        finally:
            shutil.rmtree(extracted_folder)
            os.remove(archive_filename)

    def _unzip(self, pkg_name, archive_filename):
        import uuid
        print('Extracting archive file ...')
        extracted_folder = os.path.join(os.getenv('TMPDIR'), uuid.uuid4().hex)
        os.mkdir(extracted_folder)
        if '.zip' in archive_filename:
            d = os.path.join(extracted_folder, pkg_name)
            os.mkdir(d)
            _stash('unzip -d {} {}'.format(d, archive_filename))
        elif '.bz2' in archive_filename:
            _stash('tar -C {} -jxf {}'.format(extracted_folder, archive_filename))
        else:  # gzip
            _stash('tar -C {} -zxf {}'.format(extracted_folder, archive_filename))

        return extracted_folder

    def _run_setup_file(self, filename, extras=[]):
        """
        Transform and Run AST of the setup file
        :param filename: file to run
        :type filename: str
        :param extras: extras to install
        :type extras: list of str
        :return: tuple of (files installed, dependencies)
        :rtype: tuple of (list of str, list of str)
        """

        try:
            import pkg_resources
        except ImportError:
            # pkg_resources install may be in progress
            pkg_resources = None

        namespace = {
            '_setup_stub_': _setup_stub_,
            '__file__': filename,
            '__name__': '__main__',
            'setup_args': None,
            'setup_kwargs': None,
        }

        source_folder = os.path.dirname(filename)

        tree = ArchiveFileInstaller._get_cooked_ast(filename)
        codeobj = compile(tree, filename, 'exec')

        # Some setup files import the package to be installed and sometimes opens a file
        # in the source folder. So we modify sys.path and change directory into source folder.
        saved_cwd = os.getcwd()
        saved_sys_path = sys.path[:]
        os.chdir(source_folder)
        sys.path.insert(0, source_folder)
        try:
            exec (codeobj, namespace, namespace)
        finally:
            os.chdir(saved_cwd)
            sys.path = saved_sys_path

        args, kwargs = sys.modules['setuptools']._setup_params_
        # for k in sorted(kwargs.keys()): print('{}: {!r}'.format(k, kwargs[k]))

        if 'ext_modules' in kwargs:
            ext = kwargs['ext_modules']
            if (ext is not None) and (len(ext) > 0):
                print('WARNING: Extension modules are skipped: {}'.format(ext))

        packages = kwargs['packages'] if 'packages' in kwargs else []
        py_modules = kwargs['py_modules'] if 'py_modules' in kwargs else []

        if not packages and not py_modules:
            raise PipError('failed to find packages or py_modules arguments in setup call')

        package_dirs = kwargs.get('package_dir', {})
        use_2to3 = kwargs.get('use_2to3', False) and six.PY3

        files_installed = []

        # handle scripts
        # we handle them before the packages because they may be moved
        # while handling the packages
        scripts = kwargs.get("scripts", [])
        for script in scripts:
            if self.verbose:
                print("Handling commandline script: {s}".format(s=script))
            cmdname = script.replace(os.path.dirname(script), "").replace("/", "")
            if '.' not in cmdname:
                cmdname += ".py"
            scriptpath = os.path.join(source_folder, script)
            with open(scriptpath, "r") as fin:
                content = fin.read()
            cmdpath = create_command(cmdname, content)
            files_installed.append(cmdpath)

        packages = ArchiveFileInstaller._consolidated_packages(packages)
        for p in sorted(packages):  # folders or files under source root

            if p == '':  # no packages just files
                from_folder = os.path.join(source_folder, package_dirs.get(p, ''))
                for f in ArchiveFileInstaller._find_package_files(from_folder):
                    target_file = os.path.join(self.site_packages, f)
                    ArchiveFileInstaller._safe_move(os.path.join(from_folder, f), target_file)
                    files_installed.append(target_file)
                    if use_2to3:
                        _stash('2to3 -w {} > /dev/null'.format(target_file))

            else:  # packages
                target_dir = os.path.join(self.site_packages, p)
                if p in package_dirs:
                    ArchiveFileInstaller._safe_move(os.path.join(source_folder, package_dirs[p]), target_dir)

                elif '' in package_dirs:
                    ArchiveFileInstaller._safe_move(os.path.join(source_folder, package_dirs[''], p), target_dir)

                else:
                    ArchiveFileInstaller._safe_move(os.path.join(source_folder, p), target_dir)
                files_installed.append(target_dir)
                if use_2to3:
                    _stash("""find {} --name '.py' | xargs -n 1 -I %% 2to3 -w %% > /dev/null""".format(target_dir))

        py_modules = ArchiveFileInstaller._consolidated_packages(py_modules)
        for p in sorted(py_modules):  # files or folders where the file resides, e.g. ['file', 'folder.file']

            if '' in package_dirs:
                p = os.path.join(package_dirs[''], p)

            if os.path.isdir(os.path.join(source_folder, p)):  # folder
                target_dir = os.path.join(self.site_packages, p)
                ArchiveFileInstaller._safe_move(os.path.join(source_folder, p), target_dir)
                files_installed.append(target_dir)
                if use_2to3:
                    _stash("""find {} --name '.py' | xargs -n 1 -I %% 2to3 -w %% > /dev/null""".format(target_dir))

            else:  # file
                target_file = os.path.join(self.site_packages, p + '.py')
                ArchiveFileInstaller._safe_move(os.path.join(source_folder, p + '.py'), target_file)
                files_installed.append(target_file)
                if use_2to3:
                    _stash('2to3 -w {} > /dev/null'.format(target_file))

        # handle entry points
        entry_points = kwargs.get("entry_points", {})
        if isinstance(entry_points, (six.binary_type, six.text_type)):
            if pkg_resources is not None:
                entry_points = {s: c for s, c in pkg_resources.split_sections(entry_points)}
            else:
                print("Warning: pkg_resources not available, skipping entry_points definitions.")
                entry_points = {}
        for epn in entry_points:
            if self.verbose:
                print("Handling entrypoints for: " + epn)
            ep = entry_points[epn]
            if isinstance(ep, (six.binary_type, six.text_type)):
                ep = [ep]
            if epn == "console_scripts":
                for dec in ep:
                    name, loc = dec.replace(" ", "").split("=")
                    modname, funcname = loc.split(":")
                    if not name.endswith(".py"):
                        name += ".py"
                    desc = kwargs.get("description", "")
                    path = create_command(
                        name,
                        (
                            u"""'''%s'''
from %s import %s

if __name__ == "__main__":
    %s()
""" % (desc,
                    modname,
                    funcname,
                    funcname)
                        ).encode("utf-8")
                    )
                    files_installed.append(path)
            else:
                print("Warning: passing entry points for '{n}'.".format(n=epn))

        # Recursively Handle dependencies
        dependencies = kwargs.get('install_requires', [])
        if isinstance(dependencies, (six.text_type, six.binary_type)):
            # must be split into lines
            dependencies = dependencies.splitlines()
        # add extra dependencies
        extra_req = kwargs.get("extras_require", [])
        for en in extra_req:
            if en in extras:
                dependencies += list(extra_req.get(en, []))
        return files_installed, dependencies

    @staticmethod
    def _get_cooked_ast(filename):
        """
        Get AST of the setup file and also transform it for fake setuptools
        and stub setup calls.
        """
        # with codecs.open(filename, mode="r", encoding="UTF-8") as ins:
        #    s = ins.read()
        with open(filename, "rb") as ins:
            tree = ast.parse(
                ins.read(),
                filename=filename,
                mode='exec'
            )
        ArchiveFileInstaller.SetupTransformer().visit(tree)
        return tree

    @staticmethod
    def _consolidated_packages(packages):
        packages = sorted(packages)
        consolidated = set()
        for pkg in packages:
            if '.' in pkg:
                consolidated.add(pkg.split('.')[0])  # append the root folder
            elif '/' in pkg:
                consolidated.add(pkg.split('/')[0])
            else:
                consolidated.add(pkg)
        return consolidated

    @staticmethod
    def _find_package_files(directory):
        files = []
        for f in os.listdir(directory):
            if f.endswith('.py') and f != 'setup.py' and not os.path.isdir(f):
                files.append(f)
        return files

    @staticmethod
    def _safe_move(src, dest):
        if not os.path.exists(src):
            raise PipError('cannot locate source folder/file: {}'.format(src))
        if os.path.exists(dest):
            if NO_OVERWRITE:
                raise PipError('cannot overwrite existing target, manual removal required: {}'.format(dest))
            else:
                if os.path.isdir(dest):
                    shutil.rmtree(dest)
                else:
                    os.remove(dest)
        shutil.move(src, dest)


# package_config_handler = PackageConfigHandler()
# archive_file_installer = ArchiveFileInstaller()


class PackageRepository(object):
    """
    A Package Repository is a manager class to perform various actions
    related to a package.
    This is a base class providing basic layout of a Repository.
    """

    def __init__(self, site_packages=SITE_PACKAGES_FOLDER, verbose=False):
        self.site_packages = site_packages
        self.verbose = verbose
        self.config = PackageConfigHandler(site_packages=self.site_packages, verbose=self.verbose)
        self.installer = ArchiveFileInstaller(site_packages=self.site_packages, verbose=self.verbose)

    def versions(self, pkg_name):
        raise PipError('versions only available for PyPI packages')

    def download(self, pkg_name, ver_spec):
        raise PipError('Action Not Available: download')

    def install(self, pkg_name, ver_spec, flags=DEFAULT_FLAGS, extras=[]):
        raise PipError('Action Not Available: install')

    def _install(self, pkg_name, pkg_info, archive_filename, dependency_flags=DEFAULT_FLAGS, extras=[]):
        if archive_filename.endswith(".whl"):
            print("Installing wheel: {}...".format(os.path.basename(archive_filename)))
            wheel = Wheel(archive_filename, verbose=self.verbose, extras=extras)
            files_installed, dependencies = wheel.install(self.site_packages)
        else:
            files_installed, dependencies = self.installer.run(pkg_name, archive_filename, extras=extras)
        # never install setuptools as dependency
        dependencies = [dependency for dependency in dependencies if dependency != 'setuptools']
        name_versions = [VersionSpecifier.parse_requirement(requirement) for requirement in dependencies]
        # filter (None, ...)
        name_versions = list(filter(lambda e: e[0] is not None, name_versions))
        sys.modules['setuptools']._installed_requirements_.append(pkg_name)
        pkg_info['files'] = ','.join(files_installed)
        pkg_info['dependency'] = ','.join(name_version[0] for name_version in name_versions)
        self.config.add_module(pkg_info)
        print('Package installed: {}'.format(pkg_name))

        for dep_name, ver_spec, extras in name_versions:
            
            if dep_name.strip().startswith("#") or len(dep_name.strip()) == 0:
                # not a dependency
                continue

            if dep_name == 'setuptools':  # do not install setuptools
                continue

            # Some packages have error on dependency names
            dep_name = PACKAGE_NAME_FIXER.get(dep_name, dep_name)

            # If this dependency is installed before, skipping
            # TODO: should we NOT skip if extras are specified?
            if dep_name in sys.modules['setuptools']._installed_requirements_:
                print('Dependency already installed: {}'.format(dep_name))
                continue

            if dep_name in BUNDLED_MODULES:
                print('Dependency already bundled in distribution: {}'.format(dep_name))
                continue

            print(
                'Installing dependency: {} (required by: {})'.format(
                    '{}{}'.format(dep_name,
                                  ver_spec if ver_spec else ''),
                    pkg_name
                )
            )
            repository = get_repository(dep_name, verbose=self.verbose)
            try:
                repository.install(dep_name, ver_spec, flags=dependency_flags, extras=extras)
            except PackageAlreadyInstalled:
                # well, it is already installed...
                # TODO: maybe update package if required?
                pass

    def search(self, name_fragment):
        raise PipError('search only available for PyPI packages')

    def list(self):
        modules = self.config.list_modules()
        return [(module, self.config.get_info(module)) for module in modules]

    def remove(self, pkg_name):
        if self.config.module_exists(pkg_name):
            dependencies = self.config.get_dependencies(pkg_name)
            other_dependencies = self.config.get_all_dependencies(exclude_module=(pkg_name, ))
            files_installed = self.config.get_files_installed(pkg_name)

            if files_installed:
                for f in files_installed:
                    if os.path.isdir(f):
                        shutil.rmtree(f)
                    elif os.path.isfile(f):
                        os.remove(f)
                    else:
                        print('Package may have been removed externally without using pip. Deleting from registry ...')
            else:
                if os.path.isdir(os.path.expanduser('~/Documents/site-packages/{}'.format(pkg_name.lower()))):
                    shutil.rmtree(os.path.expanduser('~/Documents/site-packages/{}'.format(pkg_name.lower())))
                elif os.path.isfile(os.path.expanduser('~/Documents/site-packages/{}.py'.format(pkg_name.lower()))):
                    os.remove(os.path.expanduser('~/Documents/site-packages/{}.py'.format(pkg_name.lower())))
                else:
                    print('Package may have been removed externally without using pip. Deleting from registry ...')

            self.config.remove_module(pkg_name)
            print('Package removed.')

            if dependencies:
                for dependency in dependencies:
                    # If not other packages depend on it, it may be subject to removal
                    if dependency not in other_dependencies:
                        # Only remove the module if it exists in the registry. Otherwise
                        # it is possibly a builtin module.
                        # For backwards compatibility, we do not remove any entries
                        # that do not have a dependency option (since they are manually
                        # installed before).
                        if self.config.module_exists(dependency) \
                        and self.config.get_dependencies(dependency) is not None:
                            print('Removing dependency: {}'.format(dependency))
                            self.remove(dependency)

        else:
            raise PipError('package not installed: {}'.format(pkg_name))

    def update(self, pkg_name):
        if self.config.module_exists(pkg_name):
            raise PipError('update only available for packages installed from PyPI')
        else:
            PipError('package not installed: {}'.format(pkg_name))


class PyPIRepository(PackageRepository):
    """
    This repository performs its actions using the PyPI as a backend store.
    """

    def __init__(self, *args, **kwargs):
        super(PyPIRepository, self).__init__(*args, **kwargs)
        try:
            import xmlrpclib
        except ImportError:
            # py3
            import xmlrpc.client as xmlrpclib
        # DO NOT USE self.pypi, it's there just for search, it's obsolete/legacy
        self.pypi = xmlrpclib.ServerProxy('https://pypi.python.org/pypi')
        self.standard_package_names = {}
    
    def _check_blocklist(self, pkg_name):
        """
        Check if a package is blocklisted.
        The result is a tuple:
            - element 0 is True if the package is blocklisted
            - element 1 is the reason
            - element 2 is True if the install should fail due to this
            - element 3 is an optional alternative package to use instead.
        :param pkg_name: name of package to check
        :type pkg_name: str
        :return: a tuple of (blocklisted, reason, fatal, alt).
        :rtype: (bool, str, bool, str or None)
        """
        if (BLOCKLIST_PATH is None) or (not os.path.exists(BLOCKLIST_PATH)):
            # blocklist not available
            return (False, "", False, None)
        with open(BLOCKLIST_PATH) as fin:
            content = json.load(fin)
        if pkg_name not in content["blocklist"]:
            # package not blocklisted
            return (False, "", False, None)
        else:
            # package blocklisted
            reasonid, fatal, alt = content["blocklist"][pkg_name]
            reason = content["reasons"].get(reasonid, reasonid)
            return (True, reason, fatal, alt)

    def get_standard_package_name(self, pkg_name):
        if pkg_name not in self.standard_package_names:
            try:
                r = requests.get('https://pypi.python.org/pypi/{}/json'.format(pkg_name))
                self.standard_package_names[pkg_name] = r.json()['info']['name']
            except:
                return pkg_name

        return self.standard_package_names[pkg_name]

    def search(self, pkg_name):
        pkg_name = self.get_standard_package_name(pkg_name)
        # XML-RPC replacement would be tricky, because we probably
        # have to use simplified / cached index to search in, can't
        # find JSON API to search for packages
        hits = self.pypi.search({'name': pkg_name}, 'and')
        if not hits:
            raise PipError('No matches found: {}'.format(pkg_name))

        hits = sorted(hits, key=lambda pkg: pkg['_pypi_ordering'], reverse=True)
        return hits

    def _package_data(self, pkg_name):
        r = requests.get('https://pypi.python.org/pypi/{}/json'.format(pkg_name))
        if not r.status_code == requests.codes.ok:
            raise PipError('Failed to fetch package release urls')

        return r.json()

    def _package_releases(self, pkg_data):
        return pkg_data['releases'].keys()

    def _package_latest_release(self, pkg_data):
        return pkg_data['info']['version']

    def _package_downloads(self, pkg_data, hit):
        return pkg_data['releases'][hit]

    def _package_info(self, pkg_data):
        return pkg_data['info']

    def versions(self, pkg_name):
        pkg_name = self.get_standard_package_name(pkg_name)
        pkg_data = self._package_data(pkg_name)
        releases = self._package_releases(pkg_data)

        if not releases:
            raise PipError('No matches found: {}'.format(pkg_name))

        return releases

    def download(self, pkg_name, ver_spec, flags=DEFAULT_FLAGS):
        print('Querying PyPI ... ')
        pkg_name = self.get_standard_package_name(pkg_name)
        pkg_data = self._package_data(pkg_name)
        hit = self._determin_hit(pkg_data, ver_spec, flags=flags)

        if self.verbose:
            print("Using {n}=={v}...".format(n=pkg_name, v=hit))

        downloads = self._package_downloads(pkg_data, hit)

        if not downloads:
            raise PipError('No download available for {}: {}'.format(pkg_name, hit))

        source = None
        wheel = None
        for download in downloads:
            if any((suffix in download['url']) for suffix in ('.zip', '.bz2', '.gz')):
                source = download
                # break
            if ".whl" in download["url"]:
                fn = download["url"][download["url"].rfind("/") + 1:]
                if wheel_is_compatible(fn):
                    wheel = download

        target = None
        if source is not None and (flags & FLAG_DIST_ALLOW_SRC > 0):
            # source is available and allowed
            if (wheel is None or (flags & FLAG_DIST_ALLOW_WHL == 0)) or (flags & FLAG_DIST_PREFER_SRC > 0):
                # no wheel is available or source is prefered
                # use source
                if self.verbose:
                    print("A source distribution is available and will be used.")
                target = source
            elif (flags & FLAG_DIST_ALLOW_WHL > 0):
                # a wheel is available and allowed and source is not preffered
                # use wheel
                if self.verbose:
                    print("A binary distribution is available and will be used.")
                target = wheel
        elif wheel is not None and (flags & FLAG_DIST_ALLOW_WHL > 0):
            # source is not available or allowed, but a wheel is available and allowed
            # use wheel
            if self.verbose:
                print("No source distribution found, but a binary distribution was found and will be used.")
            target = wheel

        if target is None:
            if self.verbose:
                print("No allowed distribution found!")
                if wheel is not None and (flags & FLAG_DIST_ALLOW_WHL == 0):
                    print("However, a wheel is available. Maybe try without '--no-binary' or with '--only-binary :all:'?")
                if source is not None and (flags & FLAG_DIST_ALLOW_SRC == 0):
                    print("However, a source distribution is available. Maybe try with '--no-binary :all:'?")
            raise PipError("No allowed distribution found for '{}': {}!".format(pkg_name, hit))

        pkg_info = self._package_info(pkg_data)
        pkg_info['url'] = 'pypi'

        print('Downloading package ...')

        worker = _stash('wget {} -o $TMPDIR/{}'.format(target['url'], target['filename']))

        if worker.state.return_value != 0:
            raise PipError('failed to download package from {}'.format(target['url']))

        return os.path.join(os.getenv('TMPDIR'), target['filename']), pkg_info

    def install(self, pkg_name, ver_spec, flags=DEFAULT_FLAGS, pip_info_file=PIP_INFO_FILE, extras=[]):
        pkg_name = self.get_standard_package_name(pkg_name)
        
        # check if package is blocklisted
        # we only do this for PyPI installs, since non-PyPI installs
        # may have the same pkg name for a different package.
        # TODO: should this be changed?
        blocklisted, reason, fatal, alt = self._check_blocklist(pkg_name)
        if blocklisted and not (flags & FLAG_IGNORE_BLOCKLIST > 0):
            if fatal:
                # raise an exception.
                print(
                    _stash.text_color(
                        "Package {} is blocklisted and marked fatal. Failing install.".format(pkg_name),
                        "red",
                        )
                    )
                print(_stash.text_color("Reason: " + reason, "red"))
                raise PackageBlocklisted(pkg_name, reason)
            elif alt is not None:
                # an alternative package exposing the same functionality
                #  and API is known. Print a warning and use this instead.
                print(
                    _stash.text_color(
                        "Warning: Using {} instead of {}".format(alt, pkg_name),
                        "yellow",
                        )
                    )
                print("Reason: " + reason)
                pkg_name = alt
                # use an empty VersionSpecifier to mark any version as acceptable
                ver_spec = _stash.libversion.VersionSpecifier()
                # do not use extras. We can not be sure that the package provide the same extras.
                extras = []
            else:
                # this package is probably bundled with pythonista
                # we should print a warning, but continue anyway
                print(
                    _stash.text_color(
                        "Warning: package '{}' is blocklisted, but marked as non-fatal.".format(pkg_name),
                        "yellow",
                        )
                    )
                print("This probably means that the dependency can not be installed, but pythonista ships with the package preinstalled.")
                print("Reason for blocklisting: " + reason)
                return
        
        if not self.config.module_exists(pkg_name):
            archive_filename, pkg_info = self.download(pkg_name, ver_spec, flags=flags)
            self._install(pkg_name, pkg_info, archive_filename, dependency_flags=flags, extras=extras)
            # save json file of info
            info_file = pip_info_file % pkg_name
            info_folder = os.path.split(info_file)[0]
            if not os.path.exists(info_folder):
                os.mkdir(info_folder)
            with open(info_file, 'w') as f:
                json.dump(pkg_info, f)
        else:
            # todo: maybe update package?
            raise PackageAlreadyInstalled('Package already installed')

    def update(self, pkg_name):
        global SITE_PACKAGES_FOLDER
        pkg_name = self.get_standard_package_name(pkg_name)
        if self.config.module_exists(pkg_name):
            pkg_data = self._package_data(pkg_name)
            hit = self._package_latest_release(pkg_data)
            current = self.config.get_info(pkg_name)
            if not current['version'] == hit:
                files_installed = self.config.get_files_installed(pkg_name)
                if files_installed:
                    SITE_PACKAGES_FOLDER = os.path.dirname(files_installed[0])
                print('Updating {} in {}'.format(pkg_name,SITE_PACKAGES_FOLDER))
                self.remove(pkg_name)
                self.install(pkg_name, VersionSpecifier((('==', hit), )))
            else:
                print('Package already up-to-date.')
        else:
            raise PipError('package not installed: {}'.format(pkg_name))

    def _determin_hit(self, pkg_data, ver_spec, flags=None):
        """
        Find a release for a package matching a specified version.
        :param pkg_data: the package information
        :type pkg_data: dict
        :param ver_spec: the version specification
        :type ver_spec: VersionSpecifier
        :param flags: (distribution) options
        :type flags: int or None
        :return: a version matching the specified version
        :rtype: str
        """
        pkg_name = pkg_data['info']['name']
        latest = self._package_latest_release(pkg_data)
        # create a sorted list of versions, newest fist.
        # we manualle  add the  latest release in front to improve the chances of finding
        # the most recent compatible version
        versions = [latest] + _stash.libversion.sort_versions(self._package_releases(pkg_data))
        for hit in versions:
            # we return the fist matching hit, so we should sort the hits by descending version
            if (flags is not None) and not self._dist_flags_allows_release(flags, pkg_data, hit):
                # hit has no source/binary release and is not allowed by dis
                continue
            if not self._release_matches_py_version(pkg_data, hit):
                # hit contains no compatible releases
                continue
            if ver_spec is None or ver_spec.match(hit):
                # version is allowed
                return hit
        else:
            raise PipError('Version not found: {}{}'.format(pkg_name, ver_spec if ver_spec is not None else ""))

    def _release_matches_py_version(self, pkg_data, release):
        """
        Check if a release is compatible with the python version.
        :param pkg_data: package information
        :type pkg_data: dict
        :param release: the release to check
        :type release: str
        :return: whether the releases matches the python version
        :rtype: boolean
        """
        had_v = False
        has_source = False
        downloads = self._package_downloads(pkg_data, release)
        for download in downloads:
            requires_python = download.get("requires_python", None)
            if requires_python is not None:
                reqs = "python" + requires_python
                name, ver_spec, extras = VersionSpecifier.parse_requirement(reqs)
                assert name == "python"  # if this if False some large bug happened...
                if ver_spec.match(platform.python_version()):
                    # compatible
                    return True
            else:
                # fallback
                # TODO: do we require this?
                pv = download.get("python_version", None)
                if pv is None:
                    continue
                elif pv in ("py2.py3", "py3.py2"):
                    # compatible with both py versions
                    return True
                elif pv.startswith("2") or pv == "py2":
                    # py2 release
                    if not six.PY3:
                        return True
                elif pv.startswith("3") or pv == "py3":
                    # py3 release
                    if six.PY3:
                        return True
                elif pv == "source":
                    # i honestly have no idea what this means
                    # i first assumed it means "this source is compatible with both", so just return True
                    # however, this seems to be wrong. Instead, we use this as a fallback yes
                    has_source = True
            had_v = True
        if had_v:
            # no allowed downloads found
            return has_source
        else:
            # none found, maybe pypi changed
            # in this case, just return True
            # we did it before without these checks and it worked *most* of the time, so missing this check is not horrible...
            return True

    def _dist_flags_allows_release(self, flags, pkg_data, release):
        """
        Check if a release is allowed by the distribution flags.
        :param flags: the (distribution) flags
        :type flags: int
        :param pkg_data: package information
        :type pkg_data: dict
        :param release: the release to check
        :type release: str
        :return: whether the flags allow this release or not
        :rtype: boolean
        """
        downloads = self._package_downloads(pkg_data, release)
        for download in downloads:
            pt = download.get("packagetype", None)
            if pt is None:
                continue
            elif pt in ("source", "sdist"):
                # source distribution
                if (flags & FLAG_DIST_ALLOW_SRC > 0):
                    return True
            elif pt in ("bdist_wheel", "wheel", "whl"):
                # wheel
                if (flags & FLAG_DIST_ALLOW_WHL > 0):
                    return True
        # no allowed downloads found
        return False


class GitHubRepository(PackageRepository):
    """
    This repository performs actions using GitHub as a backend store.
    """

    def _get_release_from_version_specifier(self, ver_spec):
        if isinstance(ver_spec, VersionSpecifier):
            try:
                for op, ver in ver_spec.specs:
                    if op == operator.eq:
                        return ver
            except ValueError:
                raise PipError('GitHub repository requires exact version match')
        else:
            return ver_spec if ver_spec is not None else 'master'

    def versions(self, owner_repo):
        owner, repo = owner_repo.split('/')
        data = requests.get('https://api.github.com/repos/{}/{}/releases'.format(owner, repo)).json()
        return [entry['name'] for entry in data]

    def download(self, owner_repo, ver_spec):
        release = self._get_release_from_version_specifier(ver_spec)

        owner, repo = owner_repo.split('/')
        metadata = requests.get('https://api.github.com/repos/{}/{}'.format(owner, repo)).json()

        _stash('wget https://github.com/{0}/{1}/archive/{2}.zip -o $TMPDIR/{2}.zip'.format(owner, repo, release))
        return os.path.join(os.getenv('TMPDIR'), release + '.zip'), {
        'name': owner_repo,
        'url': 'github',
        'version': release,
        'summary': metadata.get('description', ''),
        }

    def install(self, owner_repo, ver_spec, flags=DEFAULT_FLAGS, extras=[]):
        if not self.config.module_exists(owner_repo):
            owner, repo = owner_repo.split('/')
            release = self._get_release_from_version_specifier(ver_spec)
            archive_filename, pkg_info = self.download(owner_repo, release)
            self._install('-'.join([repo, release]), pkg_info, archive_filename, dependency_flags=flags, extras=extras)
        else:
            raise PipError('Package already installed')


class UrlRepository(PackageRepository):
    """
    This repository deals with a package from a single URL
    """

    def download(self, url, ver_spec):
        archive_filename = os.path.basename(url)
        if os.path.splitext(archive_filename)[1] not in ('.zip', '.gz', '.bz2'):
            raise PipError('cannot find a valid archive file at url: {}'.format(url))
        _stash('wget {} -o $TMPDIR/{}'.format(url, archive_filename))

        return os.path.join(os.getenv('TMPDIR'), archive_filename), {
        'name': url,
        'url': 'url',
        'version': '',
        'summary': '',
        }

    def install(self, url, ver_spec, flags=DEFAULT_FLAGS, extras=[]):
        if not self.config.module_exists(url):
            archive_filename, pkg_info = self.download(url, ver_spec)
            pkg_name = os.path.splitext(os.path.basename(archive_filename))[0]
            self._install(pkg_name, pkg_info, archive_filename, dependency_flags=flags, extras=extras)
        else:
            raise PipError('Package already installed')


class LocalRepository(PackageRepository):
    """
    This repository deals with a local archive file.
    """

    def install(self, archive_filename, ver_spec, flags=DEFAULT_FLAGS, extras=[]):
        pkg_info = {'name': archive_filename, 'url': 'local', 'version': '', 'summary': ''}
        self._install(pkg_name, pkg_info, archive_filename, dependency_flags=flags, extras=extras)


# url_repository = UrlRepository()
# local_repository = LocalRepository()
# github_repository = GitHubRepository()
# pypi_repository = PyPIRepository()


def get_repository(pkg_name, site_packages=SITE_PACKAGES_FOLDER, verbose=False):
    """
    The corresponding repository based on the given package name.
    :param pkg_name: It can be one of the four following options:
    1. An URL pointing to an archive file
    2. Path to a local archive file
    3. A owner/repo pair pointing to a GitHub repo
    4. A name representing a PyPI package.
    :param site_packages: folder containing the site-packages
    :type site_packages: str
    :param verbose: enable additional output
    :type verbose: bool
    """

    if pkg_name.startswith('http://') \
    or pkg_name.startswith('https://') \
    or pkg_name.startswith('ftp://'):  # remote archive file
        print('Working on URL repository ...')
        return UrlRepository(site_packages=site_packages, verbose=verbose)

    # local archive file
    elif os.path.isfile(pkg_name) and \
    (pkg_name.endswith('.zip') or pkg_name.endswith('.gz') or pkg_name.endswith('.bz2')):
        print('Working on Local repository ...')
        return LocalRepository(site_packages=site_packages, verbose=verbose)

    elif '/' in pkg_name:  # github, e.g. selectel/pyte
        print('Working on GitHub repository ...')
        return GitHubRepository(site_packages=site_packages, verbose=verbose)

    else:  # PyPI
        return PyPIRepository(site_packages=site_packages, verbose=verbose)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()

    ap.add_argument('--verbose', action='store_true', help='be more chatty')
    ap.add_argument(
        "-6",
        action='store_const',
        help='manage packages for py2 and py3',
        dest='site_packages',
        const=OLD_SITE_PACKAGES_FOLDER,
        default=SITE_PACKAGES_FOLDER
    )

    subparsers = ap.add_subparsers(
        dest='sub_command',
        title='List of sub-commands',
        metavar='sub-command',
        help='"pip sub-command -h" for more help on a sub-command'
    )
    
    show_parser = subparsers.add_parser('show', help='show information of package ')
    show_parser.add_argument('package', help='package name to show')
    show_parser.add_argument('-f', '--force', action="store_true", dest="forcedownload", help='force to download info file from pypi')

    list_parser = subparsers.add_parser('list', help='list packages installed')

    install_parser = subparsers.add_parser('install', help='install packages')
    install_parser.add_argument(
        'requirements',
        help='the requirement specifier for installation',
        nargs="+",
    )
    install_parser.add_argument(
        '-N',
        '--no-overwrite',
        action='store_true',
        default=False,
        help='Do not overwrite existing folder/files',
    )
    install_parser.add_argument(
        '-d',
        '--directory',
        help='target directory for installation',
    )
    install_parser.add_argument("--no-binary", action="store", help="Do not use binary packages", dest="nobinary")
    install_parser.add_argument("--only-binary", action="store", help="Do not use binary packages", dest="onlybinary")
    install_parser.add_argument(
        "--prefer-binary",
        action="store_true",
        help="Prefer older binary packages over newer source packages",  # TODO: do we actually check older sources/wheels?
        dest="preferbinary",
    )
    install_parser.add_argument("--ignore-blocklist", action="store_true", help="Ignore blocklist", dest="ignoreblocklist")

    download_parser = subparsers.add_parser('download', help='download packages')
    download_parser.add_argument(
        'requirements',
        help='the requirement specifier for download',
        nargs="+",
    )
    download_parser.add_argument(
        '-d',
        '--directory',
        help='the directory to save the downloaded file',
    )

    search_parser = subparsers.add_parser('search', help='search with the given word fragment')
    search_parser.add_argument('term', help='the word fragment to search')

    versions_parser = subparsers.add_parser('versions', help='find versions available for given package')
    versions_parser.add_argument('package_name', help='the package name')

    remove_parser = subparsers.add_parser('uninstall', help='uninstall packages')
    remove_parser.add_argument(
        'packages',
        nargs="+",
        metavar="package",
        help='packages to uninstall',
    )

    update_parser = subparsers.add_parser('update', help='update an installed package')
    update_parser.add_argument('packages', nargs="+", help='the package name')

    dev_parser = subparsers.add_parser('dev')
    dev_parser.add_argument('opt')

    ns = ap.parse_args()
    
    if ns.site_packages is None:
        # choosen site-packages dir may be unavailable on this platform, fallback to default
        print("Warning: the specified site-packages directory is unavailable, falling back to default.")
        ns.site_packages = SITE_PACKAGES_FOLDER

    try:
        if ns.sub_command == 'list':
            repository = get_repository('pypi', site_packages=ns.site_packages, verbose=ns.verbose)
            info_list = repository.list()
            for module, info in info_list:
                print('{} ({}) - {}'.format(module, info.get('version', '???'), info.get('summary', '')))

        elif ns.sub_command == 'install':
            if ns.directory is not None:
                site_packages = ns.directory
            else:
                site_packages = ns.site_packages

            flags = DEFAULT_FLAGS
            if ns.nobinary is not None:
                if ns.nobinary == ":all:":
                    # disable all binaries
                    flags = flags & ~FLAG_DIST_ALLOW_WHL
                    flags = flags & ~FLAG_DIST_PREFER_WHL
                elif ns.nobinary == ":none:":
                    # allow all binaries
                    flags = flags | FLAG_DIST_ALLOW_WHL
                else:
                    # TODO: implement this
                    print("Error: --no-binary does currently only support :all: or :none:")

            if ns.onlybinary is not None:
                if ns.onlybinary == ":all:":
                    # disable all source
                    flags = flags & ~FLAG_DIST_ALLOW_SRC
                    flags = flags & ~FLAG_DIST_PREFER_SRC

                elif ns.nobinary == ":none:":
                    # allow all source
                    flags = flags | FLAG_DIST_ALLOW_SRC
                else:
                    # TODO: implement this
                    print("Error: --only-binary does currently only support :all: or :none:")

            if ns.preferbinary:
                # set preference to wheels
                flags = flags | FLAG_DIST_PREFER_WHL | FLAG_DIST_ALLOW_WHL
                flags = flags & ~FLAG_DIST_PREFER_SRC
            
            if ns.ignoreblocklist:
                flags = flags | FLAG_IGNORE_BLOCKLIST

            for requirement in ns.requirements:
                repository = get_repository(requirement, site_packages=site_packages, verbose=ns.verbose)
                NO_OVERWRITE = ns.no_overwrite

                pkg_name, ver_spec, extras = VersionSpecifier.parse_requirement(requirement)

                with save_current_sys_modules():
                    fake_setuptools_modules()
                    ensure_pkg_resources()  # install pkg_resources if needed
                    # start with what we have installed (i.e. in the config file)
                    sys.modules['setuptools']._installed_requirements_ = repository.config.list_modules()
                    repository.install(pkg_name, ver_spec, flags=flags, extras=extras)
                    update_req_index() 

        elif ns.sub_command == 'download':
            for requirement in ns.requirements:
                repository = get_repository(requirement, site_packages=ns.site_packages, verbose=ns.verbose)
                try:
                    pkg_name, ver_spec, extras = VersionSpecifier.parse_requirement(requirement)
                except ValueError as e:
                    print("Error during parsing of the requirement : {e}".format(e=e))
                archive_filename, pkg_info = repository.download(pkg_name, ver_spec)
                directory = ns.directory or os.getcwd()
                shutil.move(archive_filename, directory)

        elif ns.sub_command == 'search':
            repository = get_repository('pypi', site_packages=ns.site_packages, verbose=ns.verbose)
            search_hits = repository.search(ns.term)
            search_hits = sorted(search_hits, key=lambda pkg: pkg['_pypi_ordering'], reverse=True)
            for hit in search_hits:
                print('{} {} - {}'.format(hit['name'], hit['version'], hit['summary']))

        elif ns.sub_command == 'versions':
            repository = get_repository(ns.package_name, site_packages=ns.site_packages, verbose=ns.verbose)
            version_hits = repository.versions(ns.package_name)
            for hit in version_hits:
                print('{} - {}'.format(ns.package_name, hit))

        elif ns.sub_command == 'uninstall':
            for package_name in ns.packages:
                repository = get_repository('pypi', site_packages=ns.site_packages, verbose=ns.verbose)
                repository.remove(package_name)
                update_req_index() 

        elif ns.sub_command == 'update':
            for package_name in ns.packages:
                repository = get_repository(package_name, site_packages=ns.site_packages, verbose=ns.verbose)

                with save_current_sys_modules():
                    fake_setuptools_modules()
                    ensure_pkg_resources()  # install pkg_resources if needed
                    # start with what we have installed (i.e. in the config file)
                    sys.modules['setuptools']._installed_requirements_ = repository.config.list_modules()
                    repository.update(package_name)

        elif ns.sub_command == 'show':
            if ns.forcedownload:
                download_info(ns.package, site_packages=ns.site_packages)
            print_info(ns.package, site_packages=ns.site_packages)

        elif ns.sub_command=='dev':
            if ns.opt=='update-index':
                update_req_index()
                print('index file updated')
            else:
                raise PipError('unknow dev option: {}'.format(ns.opt))
                sys.exit(1)

        else:
            raise PipError('unknown command: {}'.format(ns.sub_command))
            sys.exit(1)

    except PipError as e:
        print('Error: {}'.format(e))
        if ns.verbose:
            traceback.print_exc()
        sys.exit(1)
