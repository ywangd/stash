"""
StaSh install script. Also used for updates.

IMPORTANT: ensure we maintain py2 and py3 compatibility in this file!
"""
from __future__ import print_function
import os
import shutil
import sys
import requests
import zipfile
import time


DEFAULT_REPO = "ywangd"
DEFAULT_BRANCH = "master"
TMPDIR = os.environ.get('TMPDIR', os.environ.get('TMP'))
URL_TEMPLATE = 'https://github.com/{}/stash/archive/{}.zip'
TEMP_ZIPFILE = os.path.join(TMPDIR, 'StaSh.zip')
TEMP_PTI = os.path.join(TMPDIR, 'ptinstaller.py')
URL_PTI = 'https://raw.githubusercontent.com/ywangd/pythonista-tools-installer/master/ptinstaller.py'
BASE_DIR = os.path.expanduser('~')
DEFAULT_INSTALL_DIR = os.path.join(BASE_DIR, 'Documents/site-packages/stash')
DEFAULT_PTI_PATH = os.path.join(DEFAULT_INSTALL_DIR, "bin", "ptinstaller.py")
IN_PYTHONISTA = sys.executable.find('Pythonista') >= 0
PY2_COMPATIBLE = False
PY3_COMPATIBLE = True
UNWANTED_FILES = [
        'getstash.py',
        'run_tests.py',
        'testing.py',
        'dummyui.py',
        'dummyconsole.py',
        'bin/pcsm.py',
        'bin/bh.py',
        'bin/pythonista.py',
        'bin/cls.py',
        'stash.py',
        'lib/librunner.py',
        'system/shui.py',
        'system/shterminal.py',
        'system/dummyui.py',
    ]


class DownloadError(Exception):
    """
    Exception indicating a problem with a download.
    """
    pass


class IncompatibleVersion(Exception):
    """
    Exception raised when a version is incompatible.
    """
    pass


def raise_for_compatibility():
    """
    Check if this version of stash is compatible with this pythonista/... version, raising an exception if not.

    While I'd prefer to just return True/False, raising an Exception allows us to convey
    more info via the exception message.
    """
    if sys.version_info[0] == 2 and not PY2_COMPATIBLE:
        raise IncompatibleVersion("Not compatible with python2! Try using stash<=0.7.5!")
    elif sys.version_info[0] == 3 and not PY3_COMPATIBLE:
        raise IncompatibleVersion("Not compatible with python3!")


def download_stash(repo=DEFAULT_REPO, branch=DEFAULT_BRANCH, outpath=TEMP_ZIPFILE, verbose=False):
    """
    Download the StaSh zipfile from github.
    :param repo: user owning the repo to download from
    :type repo: str
    :param branch: branch to download
    :type branch: str
    :param verbose: if True, print additional information
    :type verbose: bool
    """
    url = URL_TEMPLATE.format(repo, branch)
    if verbose:
        print('Downloading {} ...'.format(url))
    r = requests.get(url, stream=True)
    file_size = r.headers.get('Content-Length')
    if file_size is not None:
        file_size = int(file_size)

    with open(outpath, 'wb') as outs:
        block_sz = 8192
        for chunk in r.iter_content(block_sz):
            outs.write(chunk)


def install_pti(url=URL_PTI, outpath=DEFAULT_PTI_PATH, verbose=False):
    """
    Download and install the pythonista tools installer.
    :param url: url to download from
    :type url: str
    :param outpath: path to save to
    :type outpath: str
    :param verbose: if True, print additional information
    :type verbose: bool
    """
    if verbose:
        print("Downloading {} to {}".format(url, outpath))
    r = requests.get(url)
    with open(outpath, 'w') as outs:
        outs.write(r.text)


def install_from_zip(path=TEMP_ZIPFILE, outpath=DEFAULT_INSTALL_DIR, launcher_path=None, verbose=False):
    """
    Install StaSh from its zipfile.
    :param path: path to zipfile
    :type path: str
    :param outpath: path to extract to
    :type outpath: str
    :param launcher_path: path to install launch_stash.py to
    :type launcher_path: str
    :param verbose: print additional information
    :type verbose: bool
    """
    unzip_into(path, outpath, verbose=verbose)
    if launcher_path is not None:
        # Move launch script to Documents for easy access
        shutil.move(os.path.join(outpath, 'launch_stash.py'), launcher_path)


def unzip_into(path, outpath, verbose=False):
    """
    Unzip zipfile at path into outpath.
    :param path: path to zipfile
    :type path: str
    :param outpath: path to extract to
    :type outpath: str
    """
    if not os.path.exists(outpath):
        os.makedirs(outpath)
    if verbose:
        print('Unzipping into %s ...' % outpath)
        
    with zipfile.ZipFile(path) as zipfp:
        toplevel_directory = None
        namelist = zipfp.namelist()
        
        # find toplevel directory name
        for name in namelist:
            if os.path.dirname(os.path.normpath(name)) == "":
                # is toplevel
                toplevel_directory = name
                break
        
        for name in namelist:
            data = zipfp.read(name)
            name = name.split(toplevel_directory, 1)[-1]  # strip the top-level directory
            if name == '':  # skip top-level directory
                continue

            fname = os.path.join(outpath, name)
            if fname.endswith('/'):  # A directory
                if not os.path.exists(fname):
                    os.makedirs(fname)
            else:
                fp = open(fname, 'wb')
                try:
                    fp.write(data)
                finally:
                    fp.close()


def remove_unwanted_files(basepath, reraise=False):
    """
    Remove unwanted files.
    :param basepath: path os StaSh installation
    :type basepath: str
    :param reraise: If True, reraise any exception occuring
    :type reraise: bool
    """
    for fname in UNWANTED_FILES:
        try:
            os.remove(os.path.join(basepath, fname))
        except:
            pass



def pythonista_install(install_path, repo=DEFAULT_REPO, branch=DEFAULT_BRANCH, launcher_path=None, zippath=None, verbose=False):
    """
    Download and install StaSh and other dependencies for pythonista.
    :param install_path: directory to install into
    :type install_path: str
    :param repo: name of user owning the github repo to download/install from
    :type repo: str
    :param branch: branch to download/install
    :type repo: str
    :param launcher_path: path to install launcher to
    :type launcher_path: str
    :param zippath: if not None, it specifies a path to a StaSh zipfile, otherwise download it from repo:branch
    :type zippath: str
    :param verbose: if True, print additional information
    :type verbose: bool
    """
    if zippath is None:
        zp = TEMP_ZIPFILE
        # download StaSh
        try:
            download_stash(repo=repo, branch=branch, outpath=zp, verbose=verbose)
        except:
            raise DownloadError("Unable to download StaSh from {}:{}".format(repo, branch))
    else:
        if verbose:
            print("Using '{}' as source.".format(zippath))
        zp = zippath
    try:
        # install StaSh
        install_from_zip(zp, install_path, launcher_path, verbose=verbose)
        # install pythonista tools installer
        # TODO: should this script realy install it?
        pti_path = os.path.join(install_path, "bin", "ptinstaller.py")
        install_pti(outpath=pti_path)
    finally:
        # cleanup
        if verbose:
            print("Cleaning up...")
        if os.path.exists(zp):
            os.remove(zp)
        remove_unwanted_files(install_path, reraise=False)


def setup_install(repo=DEFAULT_REPO, branch=DEFAULT_BRANCH, install_path=None, as_user=False, zippath=None, dryrun=False, verbose=False):
    """
    Download and install StaSh using setup.py
    :param repo: name of user owning the github repo to download/install from
    :type repo: str
    :param branch: branch to download/install
    :type repo: str
    :param install_path: path to install to (as --prefix)
    :type install_path: str
    :param as_user: install into user packages
    :type as_user: bool
    :param zippath: alternative path to zip to install from (default: download from repo:branch)
    :param dryrun: if True, pass --dry-run to setup.py
    :param verbose: if True, print additional information
    :type verbose: bool
    """
    if zippath is None:
        zp = TEMP_ZIPFILE
        # download StaSh
        try:
            download_stash(repo=repo, branch=branch, outpath=zp, verbose=verbose)
        except:
            raise DownloadError("Unable to download StaSh from {}:{}".format(repo, branch))
    else:
        zp = zippath
    tp = os.path.join(TMPDIR, "getstash-{}".format(time.time()))
    unzip_into(zp, tp, verbose=verbose)
    # run setup.py
    os.chdir(tp)
    argv = ["setup.py", "install"]
    if as_user:
        argv.append("--user")
    if install_path is not None:
        argv += ["--prefix", install_path]
    if dryrun:
        argv.append("--dry-run")
    sys.argv = argv
    fp = os.path.abspath("setup.py")
    ns = {
        "__name__": "__main__",
        "__file__": fp,
    }
    with open(fp, "rU") as fin:
        content = fin.read()
        code = compile(content, fp, "exec", dont_inherit=True)
        exec(code, ns, ns)
    

def main(defs={}):
    """
    The main function.
    :param defs: namespace which may contain additional parameters
    :type defs: dict
    """
    # read additional arguments
    # These arguments will not be defined when StaSh is normally installed,
    # but both selfupdate and tests may specify different values
    # i would like to use argparse here, but this must be compatible with older StaSh versions
    repo = defs.get("_owner", DEFAULT_REPO)                  # owner of repo
    branch = defs.get("_br", DEFAULT_BRANCH)                 # target branch
    is_update = '_IS_UPDATE' in defs                         # True if update
    install_path = defs.get("_target", None)                 # target path
    launcher_path = defs.get("_launcher_path", None)         # target path for launch_stash.py
    force_dist = defs.get("_force_dist", None)               # force install method
    zippath = defs.get("_zippath", None)                     # alternate path of zipfile to use
    dryrun = defs.get("_dryrun", None)                       # do not do anything if True
    asuser = defs.get("_asuser", None)                       # install as user if True
    
    # find out which install to use
    if force_dist is None:
        if IN_PYTHONISTA:
            dist = "pythonista"
        else:
            dist = "setup"
    else:
        dist = force_dist
    
    # check compatiblity
    try:
        raise_for_compatibility()
    except IncompatibleVersion as e:
        # inform user, then abort
        print("Installation aborted. The version of StaSh you are trying to install is incompatible!")
        print(e)
        sys.exit(1)

    if dist.lower() == "pythonista":
        if install_path is None:
            install_path = DEFAULT_INSTALL_DIR
        if launcher_path is None:
            launcher_path = os.path.join(BASE_DIR, "Documents", "launch_stash.py")
        pythonista_install(install_path, repo=repo, branch=branch, launcher_path=launcher_path, zippath=zippath, verbose=True)
    elif dist.lower() == "setup":
        setup_install(repo, branch, install_path=install_path, zippath=zippath, dryrun=dryrun, as_user=asuser, verbose=True)
    else:
        raise ValueError("Invalid install type: {}".format(dist))
        
    if not is_update:
        # print additional instructions
        print('Installation completed.')
        print('Please restart Pythonista and run launch_stash.py under the home directory to start StaSh.')


# if __name__ == "__main__":
#     print("executing main()")
#     main(locals())
    
main(locals())  # older StaSh versions do not pass __name__="__main__" to getstash.py, so we must run this on toplevel
