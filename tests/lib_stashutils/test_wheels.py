# -*- coding: utf-8 -*-
"""tests for the wheel-support"""
import six

from stash.tests.stashtest import StashTestCase


class WheelsTests(StashTestCase):
    """tests fpr the wheel-support."""

    def test_wheel_is_compatible(self):
        """test wheel_is_compatible() result"""
        from stashutils import wheels

        wheelnamecompatibility = [
            ("package-1.0.0-py2.py3-none-any.whl", True),  # full compatibility
            # full compatible with build tag
            ("package-1.0.0-2-py2.py3-none-any.whl", True),
            ("package-1.0.0-py2-none-any.whl", not six.PY3),  # only py2 compatible
            ("package-1.0.0-py3-none-any.whl", six.PY3),  # only py3 compatible
            ("package-1.0.0-py2.py3-cp33m-any.whl", False),  # incompatible abi-tag
            # incompatible platform tag
            ("package-1.0.0-py2.py3-none-linux_x86_64.whl", False),
            # incompatible abi and platform tags
            ("package-1.0.0-py2.py3-cp33m-linux_x86_64.whl", False),
            # cpython 2 incompatibility
            ("package-1.0.0-cpy2-none-any.whl", False),
            # cpython 3 incompatibility
            ("package-1.0.0-cpy3-none-any.whl", False),
        ]
        for wheelname, is_compatible in wheelnamecompatibility:
            ic = wheels.wheel_is_compatible(wheelname)
            self.assertEqual(ic, is_compatible)

    def test_wheel_is_compatible_raises(self):
        """test wheel_is_compatible() error handling"""
        from stashutils import wheels

        wrong_wheelnames = [
            "nonwheel-1.0.0-py2.py3-none-any.txt",
            "noabi-1.0.0-py2.py3-any.whl",
            "toomany-1.0.0.-py2.py3-none-any-extra-fields.whl",
        ]
        for wheelname in wrong_wheelnames:
            try:
                wheels.wheel_is_compatible(wheelname)
            except wheels.WheelError:
                pass
            else:
                raise AssertionError(
                    "wheels.wheel_is_compatible() did not raise WheelError when required.")

    def test_parse_wheel_name(self):
        """test parse_wheel_name()"""
        from stashutils import wheels

        name1 = "distribution-version-buildtag-pythontag-abitag-platformtag.whl"
        result1 = wheels.parse_wheel_name(name1)
        expected1 = {
            "distribution": "distribution",
            "version": "version",
            "build_tag": "buildtag",
            "python_tag": "pythontag",
            "abi_tag": "abitag",
            "platform_tag": "platformtag",
        }
        self.assertEqual(result1, expected1)

        name2 = "stashutils-0.7.0-py2.py3-none-any.whl"
        result2 = wheels.parse_wheel_name(name2)
        expected2 = {
            "distribution": "stashutils",
            "version": "0.7.0",
            "build_tag": None,
            "python_tag": "py2.py3",
            "abi_tag": "none",
            "platform_tag": "any",
        }
        self.assertEqual(result2, expected2)

    def test_generate_filename(self):
        """test generate_filename()"""
        from stashutils import wheels

        data = {
            "distribution": "somepackage",
            "version": "1.0.0",
            "python_tag": "py27",
        }
        expected = "somepackage-1.0.0-py27-none-any.whl"
        result = wheels.generate_filename(**data)
        self.assertEqual(result, expected)
