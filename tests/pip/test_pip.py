# -*- coding: utf-8 -*-
"""tests for the 'pip' command."""
import sys
import unittest
import pytest

from six.moves import reload_module

from stash.tests.stashtest import StashTestCase, requires_network, expected_failure_on_py3


class PipTests(StashTestCase):
    """tests for the 'pip' command."""

    def setUp(self):
        """setup the tests"""
        self.cwd = self.get_data_path()
        StashTestCase.setUp(self)

    def tearDown(self):
        """clean up a test."""
        try:
            self.purge_packages()
        except Exception as e:
            self.logger.warning("Could not purge packages: " + repr(e))
        StashTestCase.tearDown(self)

    def purge_packages(self):
        """uninstall all packages."""
        output = self.run_command("pip list", exitcode=0)
        lines = output.split("\n")
        packages = [line.split(" ")[0] for line in lines]
        for package in packages:
            if package in ("", " ", "\n"):
                continue
            self.run_command("pip uninstall " + package)

    def reload_module(self, m):
        """reload a module."""
        reload_module(m)

    def assert_did_run_setup(self, output, allow_source=True, allow_wheel=True):
        """assert that the output shows that either setup.py was successfully executed or a wheel was installed."""
        if not (("Running setup file" in output and allow_source) or ("Installing wheel:" in output and allow_wheel)):
            raise AssertionError("Output '{o}' does not seem to have installed a wheel or run setup.py!".format(o=output))
        self.assertNotIn("Failed to run setup.py", output)

    def test_help(self):
        """test 'pip --help'"""
        output = self.run_command("pip --help", exitcode=0)
        self.assertIn("pip", output)
        self.assertIn("-h", output)
        self.assertIn("--help", output)
        self.assertIn("-v", output)
        self.assertIn("-6", output)
        self.assertIn("--verbose", output)
        self.assertIn("install", output)
        self.assertIn("uninstall", output)
        self.assertIn("versions", output)
        self.assertIn("search", output)
        self.assertIn("download", output)
        self.assertIn("list", output)

    @unittest.skip('Pip is retiring and seach is disabled')
    @requires_network
    def test_search(self):
        """test 'pip search <term>'"""
        output = self.run_command("pip search pytest", exitcode=0)
        self.assertIn("pytest", output)
        # due to changing pypi search results, the following results are not guaranteed.
        # TODO: fix this
        # self.assertIn("pytest-cov", output)
        # self.assertIn("pytest-env", output)

    @requires_network
    def test_versions(self):
        """test 'pip versions <package>'."""
        output = self.run_command("pip versions pytest", exitcode=0)
        self.assertIn("pytest - 2.0.0", output)
        self.assertIn("pytest - 2.5.0", output)
        self.assertIn("pytest - 3.0.0", output)
        self.assertIn("pytest - 3.5.0", output)

    @requires_network
    def test_install_pypi_simple_1(self):
        """test 'pip install <pypi_package>' (Test 1)."""
        output = self.run_command("pip --verbose install benterfaces", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: benterfaces", output)
        try:
            import benterfaces
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    @requires_network
    def test_install_pypi_simple_2(self):
        """test 'pip install <pypi_package>' (Test 2)."""
        output = self.run_command("pip --verbose install nose", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: nose", output)
        try:
            import nose
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    # @expected_failure_on_py3
    @requires_network
    def test_install_pypi_complex_1(self):
        """test 'pip install <pypi_package>' with a complex package."""
        output = self.run_command("pip --verbose install twisted", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: Twisted", output)
        try:
            import twisted
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    @unittest.skip('@cclauss: Fix me!')
    @requires_network
    def test_install_pypi_nobinary(self):
        """test 'pip install --no-binary :all: <pypi_package>'."""
        output = self.run_command("pip --verbose install --no-binary :all: rsa", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output, allow_wheel=False)
        self.assertIn("Package installed: rsa", output)
        try:
            import benterfaces
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    @requires_network
    @pytest.mark.xfail(sys.version_info < (3, 0), reason="rsa v4.7.1 binary is not available on Py2")
    def test_install_pypi_onlybinary(self):
        """test 'pip install --only-binary :all: <pypi_package>'."""
        output = self.run_command("pip --verbose install --only-binary :all: rsa==4.5", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output, allow_source=False)
        self.assertIn("Package installed: rsa", output)
        try:
            import benterfaces
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    @requires_network
    @pytest.mark.xfail(sys.version_info < (3, 0), reason="rsa v4.7.1 raises SyntaxError on Py2")
    def test_install_command(self):
        """test 'pip install <package>' creates commandline scripts."""
        # 1. test command not yet installed
        self.run_command("pyrsa-keygen --help", exitcode=127)

        # 2. install
        output = self.run_command("pip --verbose install rsa==4.5", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: rsa", output)

        # 3. test command
        output = self.run_command("pyrsa-keygen --help", exitcode=0)
        self.assertIn("pyrsa-keygen", output)
        self.assertIn("RSA", output)

        # 4. remove package
        self.run_command("pip --verbose uninstall rsa", exitcode=0)

        # 5. ensure command not found after uninstall
        self.run_command("pyrsa-keygen --help", exitcode=127)

    @requires_network
    def test_install_pypi_version_1(self):
        """test 'pip install <pypi_package>==<specific_version_1>' (Test 1)."""
        output = self.run_command("pip --verbose install rsa==3.4.2", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: rsa", output)
        try:
            import rsa
            self.reload_module(rsa)
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))
        else:
            self.assertEqual(rsa.__version__, "3.4.2")

    @requires_network
    def test_install_pypi_version_2(self):
        """test 'pip install <pypi_package>==<specific_version_2>' (Test 2)."""
        output = self.run_command("pip --verbose install rsa==3.2.2", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: rsa", output)
        try:
            import rsa
            self.reload_module(rsa)
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))
        else:
            self.assertEqual(rsa.__version__, "3.2.2")

    @unittest.skip("test not fully working")
    @requires_network
    def test_update(self):
        """test 'pip update <pypi_package>'."""
        output = self.run_command("pip --verbose install rsa==3.2.3", exitcode=0)
        self.assertIn("Downloading package", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: rsa", output)
        try:
            import rsa
            self.reload_module(rsa)
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))
        else:
            self.assertEqual(rsa.__version__, "3.2.3")
            del rsa
        output = self.run_command("pip --verbose update rsa", exitcode=0)
        try:
            import rsa
            self.reload_module(rsa)
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))
        else:
            self.assertNotEqual(rsa.__version__, "3.2.3")
            del rsa

    def test_install_local(self):
        """test 'pip install <path/to/package/>'."""
        self.run_command("zip ./stpkg.zip ./stpkg/", exitcode=0)
        output = self.run_command("pip --verbose install stpkg.zip", exitcode=0)
        self.assertIn("Package installed: stpkg.zip", output)
        self.assertNotIn("Downloading package", output)
        self.assert_did_run_setup(output)

        try:
            import stpkg
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

        output = self.run_command("stash_pip_test", exitcode=0)
        self.assertIn("local pip test successfull!", output)

    def test_install_github(self):
        """test 'pip install <owner>/<repo>'."""
        output = self.run_command("pip --verbose install bennr01/benterfaces", exitcode=0)
        self.assertIn("Working on GitHub repository ...", output)
        self.assert_did_run_setup(output)
        self.assertIn("Package installed: benterfaces-master", output)

        try:
            import benterfaces
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

    def test_uninstall(self):
        """test 'pip uninstall <package>."""
        # 1. install package
        self.run_command("zip ./stpkg.zip ./stpkg/", exitcode=0)
        output = self.run_command("pip --verbose install stpkg.zip", exitcode=0)
        self.assertIn("Package installed: stpkg.zip", output)
        self.assertNotIn("Downloading package", output)
        self.assert_did_run_setup(output)

        # 2. test successfull install
        try:
            import stpkg
        except ImportError as e:
            self.logger.info("sys.path = " + str(sys.path))
            raise AssertionError("Could not import installed module: " + repr(e))

        # 3. uninstall package
        output = self.run_command("pip --verbose uninstall stpkg.zip", exitcode=0)
        if "stpkg" in sys.modules:
            del sys.modules["stpkg"]

        # 4. ensure import failes
        try:
            import stpkg
            raise AssertionError("can still import uninstalled package!")
        except ImportError as e:
            # expected failure
            pass
    
    def test_blocklist_fatal(self):
        """test 'pip install <blocklisted-fatal-package>'."""
        output = self.run_command("pip --verbose install pip", exitcode=1)
        self.assertIn("StaSh uses a custom version of PIP", output)
        self.assertIn("PackageBlocklisted", output)
        self.assertNotIn("Package installed: pip", output)
    
    def test_blocklist_nonfatal(self):
        """test 'pip install <blocklisted-nonfatal-package>'."""
        output = self.run_command("pip --verbose install matplotlib", exitcode=0)
        self.assertIn("Warning: package 'matplotlib' is blocklisted, but marked as non-fatal.", output)
        self.assertIn("This package is already bundled with Pythonista", output)
        self.assertNotIn("PackageBlocklisted", output)
        self.assertNotIn("Package installed: matplotlib", output)
    
    # TODO: add test for blocklist with alternative.
    
