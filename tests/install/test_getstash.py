"""
Tests for getstash.py
"""
import sys
import os
import tempfile
import time
import shutil

from stash.tests.stashtest import StashTestCase, ON_CI



class GetstashTests(StashTestCase):
    """
    Test for the installation using getstash.py
    """
    def get_source_path(self):
        """
        Return the path to the StaSh root directory
        :return: path of $STASH_ROOT
        :rtype: str
        """
        cp = sys.modules[self.stash.__module__].__file__
        rp = os.path.dirname(cp)
        return rp
        
    def get_getstash_path(self):
        """
        Return the path of getstash.py
        :return: the path of getstash.py
        :rtype: str
        """
        rp = self.get_source_path()
        gsp = os.path.join(rp, "getstash.py")
        return gsp
    
    def load_getstash(self):
        """
        Load and compile getstash.py
        :return: the compiled code
        :rtype: Code
        """
        p = self.get_getstash_path()
        with open(p, "r") as fin:
            content = fin.read()
            code = compile(content, p, "exec", dont_inherit=True)
        return code
    
    def run_getstash(self, repo=None, branch=None, install_path=None, launcher_path=None, zippath=None, dist=None, dryrun=False, asuser=False):
        """
        Run getstash with the specified arguments.
        Not all arguments may be available for all installation types.
        :param repo: repo to pass to getstash.py
        :type repo: str
        :param branch: branch to pass to getstash.py
        :type branch: str
        :param install_path: path to install into
        :type install_path: str
        :param launcher_path: path to install launcher to
        :type launcher_path: str
        :param zippath: alternative path to zipfile to install from
        :type zippath: str
        :param dist: install type to force
        :type dist: str
        :param dryrun: if True, tell the installer to not actually do anything
        :type dryrun: bool
        :param asuser: if True, install for user
        :type asuser: bool
        """
        # build namespace to run installer in
        ns = {
            "__name__": "__main__",
        }
        # we add the keys only when they are specified so getstash assumes default values.
        if repo is not None:
            ns["_owner"] = repo
        if branch is not None:
            ns["_branch"] = branch
        if install_path is not None:
            ns["_target"] = install_path
        if launcher_path is not None:
            ns["_launcher_path"] = launcher_path
        if zippath is not None:
            ns["_zippath"] = zippath
        if dist is not None:
            ns["_force_dist"] = dist
        if dryrun:
            ns["_dryrun"] = True
        if asuser:
            ns["_asuser"] = True
            
        code = self.load_getstash()

        exec(code, ns, ns)
    
    def get_new_tempdir(self, create=True):
        """
        Create a temporary directory and return the path to it.
        :param create: if True, create the directory
        :type create: bool
        :return: path to a temporary directory
        :rtype: str
        """
        tp = tempfile.gettempdir()
        p = os.path.join(tp, "stash_test_getstash" + str(time.time()))
        if not os.path.exists(p) and create:
            os.makedirs(p)
        return p
    
    def create_stash_zipfile(self):
        """
        Create a github-like zipfile from this source and return the path.
        :return: path to zipfile
        :rtype: str
        """
        tp = self.get_new_tempdir(create=True)
        toplevel_name = "stash-testing"
        toplevel = os.path.join(tp, toplevel_name)
        zipname = "{}.zip".format(toplevel)
        zippath = os.path.join(tp, zipname)
        zippath_wo_ext = os.path.splitext(zippath)[0]
        sourcepath = self.get_source_path()
        shutil.copytree(sourcepath, toplevel)
        shutil.make_archive(zippath_wo_ext, "zip", tp, toplevel_name)
        return zippath
        
    
    def test_getstash_exists(self):
        """
        Check that getstash.py exists in the right repository
        You should NOT modify this test. 'getstash.py' **must** be in the root directory for selfupdate to work.
        """
        p = self.get_getstash_path()
        self.assertTrue(os.path.exists(p), "getstash.py not in StaSh root directory!")
    
    def test_getstash_compiles(self):
        """
        Test that getstash.py successfully compiles.
        """
        self.load_getstash()
    
    def test_install_pythonista(self):
        """
        Run a dummy install for pythonista.
        """
        zp = self.create_stash_zipfile()
        td = self.get_new_tempdir()
        sd = os.path.join(td, "stash")
        lp = os.path.join(td, "launch_stash.py")
        self.run_getstash(install_path=sd, launcher_path=lp, zippath=zp, dist="pythonista")
        expected = [
            "bin",
            "system",
            "man",
            "lib",
        ]
        self.assertTrue(os.path.exists(sd), "StaSh base directory not found after install!")
        self.assertTrue(os.path.exists(lp), "'launch_stash.py' not found after install!")
        for fn in expected:
            p = os.path.join(sd, fn)
            self.assertTrue(os.path.exists(sd), "'{}' not found after install!".format(p))
    
    def test_install_setup(self):
        """
        Run a dummy install using setup.py install
        """
        zp = self.create_stash_zipfile()
        td = self.get_new_tempdir()
        sd = os.path.join(td, "stash")
        asuser = (not ON_CI)
        self.run_getstash(zippath=zp, dist="setup", asuser=asuser, dryrun=True)
        
