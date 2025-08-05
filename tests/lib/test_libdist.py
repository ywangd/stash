"""
Test for 'libdist'.
"""

from stash.tests.stashtest import StashTestCase


class LibDistTests(StashTestCase):
    """
    Tests for 'libdist'
    """

    def test_libdist_is_loaded(self):
        """
        Test that 'libdist' is loaded.
        """
        loaded_libs = [an for an in dir(self.stash) if an.startswith("lib")]
        self.assertIn("libdist", loaded_libs)

    def test_clipboard_api_available(self):
        """
        Test that the clipboard api is provided by libdist
        """
        defs = dir(self.stash.libdist)
        self.assertIn("clipboard_get", defs)
        self.assertIn("clipboard_set", defs)

    def test_pip_definitions_available(self):
        """
        Test that the libdist provides the definitions required by 'pip'.
        """
        defs = dir(self.stash.libdist)
        required = ["SITE_PACKAGES_FOLDER", "SITE_PACKAGES_FOLDER_6", "BUNDLED_MODULES"]
        for an in required:
            self.assertIn(an, defs)
