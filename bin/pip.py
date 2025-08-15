# -*- coding: utf-8 -*-
"""
Install pip package manager
Wraps real pip for StaSh
"""

import re
import shutil
import sys
import requests
from pathlib import Path
import ssl

try:
    from pip._internal.cli.main import main

    _HAS_PIP = True
except ImportError:
    _HAS_PIP = False

ssl._create_default_https_context = ssl._create_unverified_context

v_maj, v_min, v_patch, *_ = sys.version_info
assert v_maj >= 3, "Python 3.10 or a more recent version is required."
assert v_min >= 10, "Python 3.10 or a more recent version is required."

_HOME = Path("~").expanduser()
_DOCUMENTS = _HOME / "Documents"
_SITE_PACKAGES = _DOCUMENTS / "site-packages"
_PREFIX_LIB = _SITE_PACKAGES / "lib"
_PREFIX_DIR_NAME = f"python{sys.version_info.major}.{sys.version_info.minor}"
_PREFIX_SITE_PACKAGES = _PREFIX_LIB / _PREFIX_DIR_NAME / "site-packages"
_PIP_BOOTSTRAP_URL = "https://bootstrap.pypa.io/get-pip.py"


def _download_and_install_pip():
    code = requests.get(_PIP_BOOTSTRAP_URL).content.decode(errors="ignore")
    # This is the dangerous part
    try:
        exec(code, {"__name__": "__main__"})
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    _SITE_PACKAGES.mkdir(parents=True, exist_ok=True)
    _PREFIX_SITE_PACKAGES.mkdir(parents=True, exist_ok=True)

    if _HAS_PIP:
        sys.argv[0] = re.sub(r"(-script\.pyw?|\.exe)?$", "", sys.argv[0])
        if "install" in sys.argv:
            if "--prefix" not in sys.argv and "--target" not in sys.argv:
                sys.argv.extend(["--prefix", _SITE_PACKAGES])
            ret = 0
            try:
                ret = main()
                shutil.copytree(_PREFIX_SITE_PACKAGES, _SITE_PACKAGES, dirs_exist_ok=True)
            finally:
                shutil.rmtree(_PREFIX_LIB)
            sys.exit(ret)
        else:
            sys.exit(main())

    else:
        print("Pip doesn't seem to be installed")
        try_install = input("Do you want to install Pip? [Y/n]")
        if try_install.lower() in {"y", "yes"}:
            print("Installing Pip")
            try:
                _download_and_install_pip()
                print("Pip installation done!")
                print("Please Restart Pythonista!")
            except Exception as e:
                print(e)
        else:
            print("Aborting installation")
