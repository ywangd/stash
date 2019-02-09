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
            ("test_2 == 7.3.12", "test_2", [(operator.eq, "7.3.12")]),
            ("with1number == 923.1512.12412", "with1number",[(operator.eq, "923.1512.12412")]),
            ("tge >= 2.0.1", "tge", [(operator.ge, "2.0.1")]),
            ("tgt > 3.0.0", "tgt", [(operator.gt, "3.0.0")]),
            ("tne != 7.0.0", "tne", [(operator.ne, "7.0.0")]),
            ("pkg_b (< 0.7.0", "pkg_b", [(operator.lt, "0.7.0")]),
            ("nondigitver <= 1.5.3b", "nondigitver", [(operator.le, "1.5.3b")]),
            ("wrapt < 2, >= 1", "wrapt", [(operator.lt, "2"), (operator.ge, "1")]),
        ]
        for req, pkg, spec in to_test:
            name, ver_spec = self.stash.libversion.VersionSpecifier.parse_requirement(req)
            self.assertEqual(name, pkg)
            if self.stash.PY3:
                # in py3, assertItemsEqual has been renamed to assertCountEqual
                self.assertCountEqual(ver_spec.specs, spec)
            else:
                self.assertItemsEqual(ver_spec.specs, spec)

    def test_version_specifier_match(self):
        """test 'libversion.VersionSpecifier().match()'"""
        to_test = [
            # format: (requirement_str, [(testversion, result)])
            ("eqtest == 1.0.0", [("1.0.0", True), ("1.0.1", False), ("1.0.0.0", False), ("11.0.0", False), ("0.1.0.0", False), ("0.9.0", False)]),
            ("lttest <= 2.0.0", [("2.0.0", True), ("2.0.1", False), ("3.0.0", False), ("1.0.0", True), ("1.9.0", True), ("11.0.0", False), ("1.9.2b", True)]),
            ("gttest >= 3.5.0", [("3.5.0", True), ("3.4.9", False), ("3.6.0", True), ("11.0.0", True), ("3.5.0a", False), ("1.0.0", False)]),
            ("eqstr == str", [("1.0.0", False), ("str", True), ("str2", False), ("s", False), ("99.999.99", False)]),
            ("wrapt < 2, >= 1", [("0.0.1", False), ("1.0.0", True), ("1.5.0", True), ("2.0.0", False), ("1.9.9", True)]),
        ]
        for rs, test in to_test:
            _, ver_spec = self.stash.libversion.VersionSpecifier.parse_requirement(rs)
            for ts, expected in test:
                result = ver_spec.match(ts)
                self.assertEqual(result, expected)

    def test_sort_versions_main(self):
        """test 'libversion.sort_versions()' for main versions"""
        raw = ["1.0.0", "0.5.0", "0.6.0", "0.5.9", "11.0.3", "11.0.4", "0.1.0", "5.7.0"]
        expected = ["11.0.4", "11.0.3", "5.7.0", "1.0.0", "0.6.0", "0.5.9", "0.5.0", "0.1.0"]
        sortedres = self.stash.libversion.sort_versions(raw)
        self.assertEqual(sortedres, expected)

    def test_sort_versions_post(self):
        """test 'libversion.sort_versions()' for post release number"""
        raw = ["1.0.0", "1.0.0.post2", "1.0.0.post3", "1.0.0-post1", "1.0.0.post"]
        expected = ["1.0.0.post3", "1.0.0.post2", "1.0.0-post1", "1.0.0.post", "1.0.0"]
        sortedres = self.stash.libversion.sort_versions(raw)
        self.assertEqual(sortedres, expected)

    def test_sort_versions_type(self):
        """test 'libversion.sort_versions()' for release type"""
        raw = ["1.0.0b", "1.0.0rc", "1.0.0a", "1.0.0a2", "1.0.0", "1.0.0.post1", "1.0.0a.dev2", "1.0.0a.dev3", "1!0.5.0", "0.5.0", "1.0.0a.dev1"]
        expected = ["1!0.5.0", "1.0.0.post1", "1.0.0", "1.0.0rc", "1.0.0b", "1.0.0a2", "1.0.0a", "1.0.0a.dev3", "1.0.0a.dev2", "1.0.0a.dev1", "0.5.0"]
        sortedres = self.stash.libversion.sort_versions(raw)
        self.assertEqual(sortedres, expected)

    def test_version_parse(self):
        """test 'libversion.Version.parse()''"""
        to_test = [
            # format: (s, {key_to_check: expected_value, ...})
            ("1.2.3", {"epoch": 0, "versiontuple": (1, 2, 3), "is_postrelease": False}),
            ("1!2.3", {"epoch": 1, "versiontuple": (2, 3), "is_devrelease": False}),
            ("5.5.4a.post5", {"versiontuple": (5, 5, 4), "rtype": self.stash.libversion.Version.TYPE_ALPHA, "is_postrelease": True, "postrelease": 5}),
            ("0.0.1rc5.dev7", {"versiontuple": (0, 0, 1), "rtype": self.stash.libversion.Version.TYPE_RELEASE_CANDIDATE, "subversion": 5, "is_devrelease": True, "devrelease": 7, "is_postrelease": False}),
            ("0.8.4.post.dev", {"versiontuple": (0, 8, 4), "is_postrelease": True, "postrelease": 0, "is_devrelease": True}),
        ]
        for vs, ea in to_test:
            version = self.stash.libversion.Version.parse(vs)
            self.assertIsInstance(version, self.stash.libversion.Version)
            for ean in ea.keys():
                eav = ea[ean]
                assert hasattr(version, ean)
                self.assertEqual(getattr(version, ean), eav)

    def test_version_cmp(self):
        """test comparsion of 'libversion.Version()'-instances"""
        to_test = [
            # format: (vs1, op, vs2, res)
            # testdata for general equality
            ("1.0.0", operator.eq, "1.0.0", True),
            ("1.0.0", operator.eq, "0!1.0.0", True),
            ("1.0.0", operator.eq, "1!1.0.0", False),
            ("1.0.0", operator.eq, "1.0.0.post", False),
            ("1.0.0", operator.eq, "1.0.0a", False),
            ("1.0.0", operator.eq, "1.0.0b", False),
            ("1.0.0.post1", operator.eq, "1.0.0.post2", False),
            ("1.0.0.post", operator.eq, "1.0.0.post0", True),
            ("1.0.0.post", operator.eq, "1.0.0.dev", False),
            # testdata for main version comparsion
            ("1.2.3", operator.eq, "1.5.0", False),
            ("2.0.3", operator.gt, "1.9.7", True),
            ("1.9.7", operator.gt, "2.0.3", False),
            ("1.9.7", operator.lt, "2.0.3", True),
            ("1.9.7", operator.lt, "1.9.7", False),
            ("1.9.7", operator.le, "1.9.7", True),
            ("2.4.9", operator.gt, "11.0.5", False),
            ("2.4.9", operator.gt, "1.0.5", True),
            ("2.4.9", operator.gt, "2.5.1", False),
            ("2.5.2", operator.gt, "2.5.1", True),
            # testdata for rtype comparsion
            ("1.0.0", operator.eq, "1.0.0a", False),
            ("1.0.0", operator.eq, "1.0.0b", False),
            ("1.0.0", operator.eq, "1.0.0rc", False),
            ("1.0.0a", operator.eq, "1.0.0b", False),
            ("1.0.0a", operator.eq, "1.0.0rc", False),
            ("1.0.0b", operator.eq, "1.0.0rc", False),
            ("1.0.0", operator.gt, "1.0.0rc", True),
            ("1.0.0rc", operator.gt, "1.0.0b", True),
            ("1.0.0b", operator.gt, "1.0.0a", True),
            ("1.0.0", operator.gt, "1.0.0b", True),
            ("1.0.0", operator.gt, "1.0.0a", True),
            ("1.0.0rc", operator.gt, "1.0.0a", True),
            # testdata for dev version comparsion
            ("1.0.0", operator.gt, "1.0.0.dev", True),
            ("1.0.0", operator.gt, "1.0.0.dev1000", True),
            ("1.0.0.dev", operator.gt, "1.0.0", False),
            ("1.0.0.dev2", operator.gt, "1.0.0.dev", True),
        ]
        for vs1, op, vs2, expected in to_test:
            v1 = self.stash.libversion.Version.parse(vs1)
            v2 = self.stash.libversion.Version.parse(vs2)
            self.assertEqual(op(v1, v2), expected)

