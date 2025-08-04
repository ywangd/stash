"""
Setup.py for StaSh on PC.
If you want to install on pythonista instead, run "import requests as r; exec(r.get('https://bit.ly/get-stash').text)"
"""

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

from setuptools import setup

if __name__ == "__main__":
    setup()
