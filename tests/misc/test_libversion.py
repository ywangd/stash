"""tests for libversion"""
import operator

from stash.tests.stashtest import StashTestCase


class LibVersionTests(StashTestCase):
    """Tests for the 'libversion' module"""
    def test_is_loaded(self):
        """assert that the 'libversion' module is loaded by StaSh"""
        assert hasattr(self.stash, "libversion")
        self.assertIsNotNone(self.stash)

    def test_import(self):
        """test that the libversion module can be imported"""
        # $STASH_ROOT/lib/ *should* be in sys.path, thus an import should be possible
        import libversion

    def test_version_specifier_parse(self):
        """test 'libversion.VersionSpecifier.parse_requirement()'"""
        to_test = [
            # format: (requirement_str, pkg_name, [(op1, v1), ...])
            ("test==1.2.3", "test", [(operator.eq, "1.2.3")]),
            ("test_2 == 7.3.12", "test2", [(operator.eq, "1.2.3")]),
            ("with1number == 923.1512.12412", "with1number",[(operator.eq, "923.1512.12412")]),
            ("tge >= 2.0.1", "tge", [(operator.ge, "2.0.1")]),
            ("tgt > 3.0.0", "tgt", [(operator.gt, "3.0.0")]),
            ("tne != 7.0.0", "tne", [(operator.ne, "7.0.0")]),
            ("pkg_b (< 0.7.0", "okg_b", [(operator.lt, "0.7.0")]),
            ("nondigitver <= 1.5.3b", [(operator.le, "1.5.3b")]),
        ]
        for req, pkg, spec in to_test:
            name, ver_spec = self.stash.libversion.VersionSpecifier.parse_requirement(req)
            self.assertEqual(name, pkg)
            self.assertItemsEqual(ver_spec.specs, spec)

    def test_version_specifier_match(self):
        """test 'libversion.VersionSpecifier().match()'"""
        to_test = {
            # format: (requirement_str, [(testversion, result)])
            ("eqtest == 1.0.0", [("1.0.0", True), ("1.0.1", False), ("1.0.0.0", False), ("11.0.0", False), ("0.1.0.0", False), ("0.9.0", False)]),
            ("lttest <= 2.0.0", [("2.0.0", True), ("2.0.1", False), ("3.0.0", False), ("1.0.0", True), ("1.9.0", True), ("11.0.0", False), ("1.9.2b", True)]),
            ("gttest >= 3.5.0", [("3.5.0", True), ("3.4.9", False), ("3.6.0", True), ("11.0.0", True), ("3.5.0a", True), ("1.0.0", False)]),
            ("eqstr == str", [("1.0.0", False), ("str", True), ("str2", False), ("s", False), ("99.999.99", False)]),
        }
        for rs, test in to_test:
            ver_spec = self.stash.libversion.VersionSpecifier.parse_requirement(rs)
            ts, expected = test
            result = ver_spec.match(ts)
            self.assertEqual(result, expected)

    def test_sort_versions_main(self):
        """test 'libversion.sort_versions()' for main versions"""
        raw = ["1.0.0", "0.5.0", "0.6.0", "0.5.9", "11.0.3", "11.0.4", "0.1.0", "5.7.0"]
        expected = ["11.0.4", "11.0.3", "5.7.0", "1.0.0", "0.6.0", "0.5.9", "0.5.0", "0.1.0"]
        sorted = self.stash.libversion.sort_versions(raw)
        self.assertEqual(raw, expected)

    def test_sort_versions_post(self):
        """test 'libversion.sort_versions()' for post release number"""
        raw = ["1.0.0", "1.0.0.post2", "1.0.0.post3", "1.0.0-post1", "1.0.0.post"]
        expected = ["1.0.0.post3", "1.0.0.post2", "1.0.0-post1", "1.0.0.post", "1.0.0"]
        sorted = self.stash.libversion.sort_versions(raw)
        self.assertEqual(raw, expected)

    def test_sort_versions_type(self):
        """test 'libversion.sort_versions()' for release type"""
        raw = ["1.0.0b", "1.0.0rc", "1.0.0a", "1.0.0a2", "1.0.0", "1.0.0.post1", "1.0.0a.dev2", "1.0.0a.dev3", "1!0.5.0", "0.5.0", "1.0.0a.dev1"]
        expected = ["1!0.5.0", "1.0.0.post1", "1.0.0", "1.0.0rc", "1.0.0b", "1.0.0a2", "1.0.0a", "1.0.0a.dev3", "1.0.0a.dev2", "1.0.0a.dev1", "0.5.0"]
        sorted = self.stash.libversion.sort_versions(raw)
        self.assertEqual(raw, expected)
