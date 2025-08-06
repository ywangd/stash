"""
Setup.py for StaSh on PC.
If you want to install on pythonista instead, run "import requests as r; exec(r.get('https://bit.ly/get-stash').text)"
"""

import ast
import os
import sys


# =================== check if run inside pythonista ===================
IN_PYTHONISTA = sys.executable.find("Pythonista") >= 0

if IN_PYTHONISTA:
    print("It appears that you are running this file using the pythonista app.")
    print("The setup.py file is intended for the installation on a PC.")
    print("Please choose one of the following options:")
    print("[1] run pythonista-specific installer")
    print("[2] continue with setup")
    print("[3] abort")
    try:
        v = int(input(">"))
    except Exception:
        v = None
    if v == 1:
        # pythonista install
        cmd = "import requests as r; exec(r.get('https://bit.ly/get-stash').text)"
        print('Executing: "' + cmd + '"')
        exec(cmd)
        sys.exit(0)
    elif v == 2:
        # continue
        pass
    else:
        # exit
        if v != 3:
            print("Unknown input!")
        print("Aborting...")
        sys.exit(1)


# =================== SETUP ===================

from setuptools import setup, find_packages

if sys.version_info.major == 2:
    INSTALL_REQUIREMENTS = [
        "rsa==4.5",
        "six",  # required by StaSh
        "pyperclip",  # required by libdist for copy/paste on PC
        "requests==2.9.1",
        "pycrypto==2.6",
        "pyte==0.8.1",
    ]
    TEST_REQUIREMENTS = [
        "pyparsing==2.0.2",
        "pytest==4.6.11",
        "flake8>=3.7.9",
    ]
else:
    INSTALL_REQUIREMENTS = (
        [
            "six",  # required by StaSh
            "pyperclip",  # required by libdist for copy/paste on PC
            "requests",
            "pycrypto",
            "pyte",
        ],
    )
    TEST_REQUIREMENTS = [
        "pyparsing",
        "pytest",
        "flake8>=3.7.9",
    ]


PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STASH_DIR = os.path.dirname(os.path.abspath(__file__))
CORE_PATH = os.path.join(STASH_DIR, "core.py")
TO_IGNORE = [os.path.abspath(os.path.join(STASH_DIR, p)) for p in ("build", "dist")]


def get_package_data_files(directory, exclude=[]):
    """
    Find data files recursibely.
    Original version from: https://stackoverflow.com/questions/27664504/how-to-add-package-data-recursively-in-python-setup-py
    :param directory: directory to search recursively
    :type directory: str
    :param exclude: list of absolute paths to ignore
    :type exclude: list of str
    :return: package data files to include
    :rtype: list of str
    """
    paths = []
    for path, directories, filenames in os.walk(directory):
        for filename in filenames:
            fp = os.path.abspath(os.path.join("..", path, filename))
            skip = False
            for v in exclude:
                if fp.startswith(v):
                    skip = True
            if not skip:
                paths.append(fp)
    return paths


def get_stash_version(corepath):
    """
    Find and return the current StaSh version.
    :param corepath: path to the 'core.py' file in the StaSh root directory
    :type corepath: str
    :return: the StaSh version defined in the corepath
    :rtype: str
    """
    with open(corepath, "r") as fin:
        for line in fin:
            if line.startswith("__version__"):
                version = ast.literal_eval(line.split("=")[1].strip())
                return version
    raise Exception("Could not find StaSh version in file '{f}'", f=corepath)


# before we start with the setup, we must be outside of the stash root path.
os.chdir(STASH_DIR)
print(STASH_DIR)


setup(
    name="StaSh",
    version=get_stash_version(CORE_PATH),
    description="StaSh for PC",
    author="https://github.com/ywangd and various contributors",
    url="https://github.com/ywangd/stash/",
    packages=[
        "stash",
        "stash.system",
        "stash.system.shui",
        "stash.lib",
    ],
    package_dir={
        "": STASH_DIR,
        "stash": STASH_DIR,
    },
    package_data={
        "": get_package_data_files(STASH_DIR, exclude=TO_IGNORE),
    },
    scripts=[os.path.join(STASH_DIR, "launch_stash.py")],
    zip_safe=False,
    install_requires=INSTALL_REQUIREMENTS,
    extras_require={
        "testing": TEST_REQUIREMENTS,
    },
)
