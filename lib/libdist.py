"""
OS/device specific interfaces
"""

import os
import sys


IN_PYTHONISTA = sys.executable.find("Pythonista") >= 0
ON_TRAVIS = "TRAVIS" in os.environ


# ========================== PYTHONISTA =======================
if IN_PYTHONISTA:
    # ------------- clipboard --------------
    import clipboard

    def clipboard_get():
        """
        Get the clipboard content.
        :return: clipboard content
        :rtype: str
        """
        return clipboard.get()

    def clipboard_set(s):
        """
        Set the clipboard content.
        :param s: string to set
        :type s: str
        """
        # TODO: non-unicode support
        assert isinstance(s, str)
        clipboard.set(s)

    # -------------- pip ----------------------

    SITE_PACKAGES_DIR_NAME = "site-packages"
    if sys.version_info < (3, 10):  # Pythonista < v3.4
        SITE_PACKAGES_DIR_NAME += "-3"

    SITE_PACKAGES_DIR_NAME_6 = "site-packages"
    SITE_PACKAGES_FOLDER = os.path.expanduser(
        "~/Documents/{}".format(SITE_PACKAGES_DIR_NAME)
    )
    SITE_PACKAGES_FOLDER_6 = os.path.expanduser(
        "~/Documents/{}".format(SITE_PACKAGES_DIR_NAME_6)
    )

    BUNDLED_MODULES = [
        "bottle",
        "beautifulsoup4",
        "pycrypto",
        "py-dateutil",
        "dropbox",
        "ecdsa",
        "evernote",
        "Faker",
        "feedparser",
        "flask",
        "html2text",
        "html5lib",
        "httplib2",
        "itsdangerous",
        "jedi",
        "jinja2",
        "markdown",
        "markdown2",
        "matplotlib",
        "mechanize",
        "midiutil",
        "mpmath",
        "numpy",
        "oauth2",
        "paramiko",
        "parsedatetime",
        "Pillow",
        "pycparser",
        "pyflakes",
        "pygments",
        "pyparsing",
        "PyPDF2",
        "pytz",
        "qrcode",
        "reportlab",
        "requests",
        "simpy",
        "six",
        "sqlalchemy",
        "pysqlite",
        "sympy",
        "thrift",
        "werkzeug",
        "wsgiref",
        "pisa",
        "xmltodict",
        "PyYAML",
    ]

    # -------------- open in / quicklook ----------------------
    import console
    from objc_util import on_main_thread

    @on_main_thread
    def open_in(path):
        """
        Open a file in another application.
        If possible, let the user decide the application
        :param path: path to file
        :type path: str
        """
        console.open_in(path)

    @on_main_thread
    def quicklook(path):
        """
        Show a preview of the file.
        :param path: path to file
        :type path: str
        """
        console.quicklook(path)

# ======================== DEFAULT / PC / travis =========================
else:
    # ------------- clipboard --------------
    # travis is a variation of PC
    if not ON_TRAVIS:
        # use pyperclip
        import pyperclip

        def clipboard_get():
            """
            Get the clipboard content.
            :return: clipboard content
            :rtype: str
            """
            return pyperclip.paste()

        def clipboard_set(s):
            """
            Set the clipboard content.
            :param s: string to set
            :type s: str
            """
            # TODO: non-unicode support
            assert isinstance(s, str)
            pyperclip.copy(s)
    else:
        # use fake implementation
        global _CLIPBOARD
        _CLIPBOARD = ""

        def clipboard_get():
            """
            Get the clipboard content.
            :return: clipboard content
            :rtype: str
            """
            return _CLIPBOARD

        def clipboard_set(s):
            """
            Set the clipboard content.
            :param s: string to set
            :type s: str
            """
            global _CLIPBOARD
            assert isinstance(s, str)
            _CLIPBOARD = s

    # -------------- pip ----------------------
    import site

    try:
        SITE_PACKAGES_FOLDER = site.getsitepackages()[0]
    except AttributeError:
        # site.getsitepackages() unavalaible in virtualenv
        import stash

        SITE_PACKAGES_FOLDER = os.path.dirname(stash.__path__[0])
    SITE_PACKAGES_FOLDER_6 = None

    BUNDLED_MODULES = [
        "six",
    ]

    # -------------- open in / quicklook ----------------------
    import webbrowser

    def open_in(path):
        """
        Open a file in another application.
        If possible, let the user decide the application
        :param path: path to file
        :type path: str
        """
        webbrowser.open(path, new=1)

    def quicklook(path):
        """
        Show a preview of the file.
        :param path: path to file
        :type path: str
        """
        webbrowser.open(path, new=1)
