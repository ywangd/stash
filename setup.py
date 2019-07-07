"""
Setup.py for StaSh on PC.
If you want to install on pythonista instead, run "import requests as r; exec(r.get('https://bit.ly/get-stash').text)"
"""
import ast
import os
import sys


# =================== check if run inside pythonista ===================
IN_PYTHONISTA = sys.executable.find('Pythonista') >= 0

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

from distutils.core import setup
from setuptools import find_packages


TEST_REQUIREMENTS = [
    "pyparsing==2.0.1",
    "pytest>=3.6.0",
    "flake8>=3.5.0",
    "pycrypto==2.6",
    "requests==2.9.1",
]


def get_package_data_files(directory):
    """
    Find data files recursibely.
    from: https://stackoverflow.com/questions/27664504/how-to-add-package-data-recursively-in-python-setup-py
    """
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
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
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


setup(
    name="StaSh",
    version=get_stash_version("stash/core.py"),
    description="StaSh for PC",
    author="https://github.com/ywangd and various contributors",
    url="https://github.com/ywangd/stash/",
    packages=[
        "stash",
        "stash.system",
        "stash.system.shui",
        "stash.lib",
    ],
    package_data={
        "": get_package_data_files("stash"),
    },
    scripts=["stash/launch_stash.py"],
    zip_safe=False,
    install_requires=[
        "six",      # required by StaSh
        "pyperclip",  # required by libdist for copy/paste on PC
    ],
    extras_require={
        "testing": TEST_REQUIREMENTS,
    },
)
