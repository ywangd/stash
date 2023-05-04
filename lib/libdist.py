"""
OS/device specific interfaces
"""
import os
import sys

import six


IN_PYTHONISTA = "Pythonista" in sys.executable
ON_CI = "CI" in os.environ


# ========================== PYTHONISTA =======================
if IN_PYTHONISTA:
    
    # ------------- clipboard --------------
    import clipboard
    
    def clipboard_get():
        """
        Get the clipboard content.
        :return: clipboard content
        :rtype: six.text_type
        """
        return clipboard.get()
    
    def clipboard_set(s):
        """
        Set the clipboard content.
        :param s: string to set
        :type s: six.text_type
        """
        # TODO: non-unicode support
        assert isinstance(s, six.text_type)
        clipboard.set(s)
    
    # -------------- pip ----------------------
    
    if six.PY3:
        SITE_PACKAGES_DIR_NAME = "site-packages"
        if sys.version_info < (3, 10):  # Pythonista < v3.4
            SITE_PACKAGES_DIR_NAME += "-3"
    else:
        SITE_PACKAGES_DIR_NAME = "site-packages-2"
    SITE_PACKAGES_DIR_NAME_6 = "site-packages"
    SITE_PACKAGES_FOLDER = os.path.expanduser('~/Documents/{}'.format(SITE_PACKAGES_DIR_NAME))
    SITE_PACKAGES_FOLDER_6 = os.path.expanduser('~/Documents/{}'.format(SITE_PACKAGES_DIR_NAME_6))
    
    BUNDLED_MODULES = [
        'bottle',
        'beautifulsoup4',
        'pycrypto',
        'py-dateutil',
        'dropbox',
        'ecdsa',
        'evernote',
        'Faker',
        'feedparser',
        'flask',
        'html2text',
        'html5lib',
        'httplib2',
        'itsdangerous',
        'jedi',
        'jinja2',
        'markdown',
        'markdown2',
        'matplotlib',
        'mechanize',
        'midiutil',
        'mpmath',
        'numpy',
        'oauth2',
        'paramiko',
        'parsedatetime',
        'Pillow',
        'pycparser',
        'pyflakes',
        'pygments',
        'pyparsing',
        'PyPDF2',
        'pytz',
        'qrcode',
        'reportlab',
        'requests',
        'simpy',
        'six',
        'sqlalchemy',
        'pysqlite',
        'sympy',
        'thrift',
        'werkzeug',
        'wsgiref',
        'pisa',
        'xmltodict',
        'PyYAML',
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
        
# ======================== DEFAULT / PC / GitHub Actions =========================
else:
    
    # ------------- clipboard --------------
    # ON_CI is a variation of PC
    if not ON_CI:
        # use pyperclip
        import pyperclip
        
        def clipboard_get():
            """
            Get the clipboard content.
            :return: clipboard content
            :rtype: six.text_type
            """
            return pyperclip.paste()
        
        def clipboard_set(s):
            """
            Set the clipboard content.
            :param s: string to set
            :type s: six.text_type
            """
            # TODO: non-unicode support
            assert isinstance(s, six.text_type)
            pyperclip.copy(s)
    else:
        # use fake implementation
        global _CLIPBOARD
        _CLIPBOARD = u""
        
        def clipboard_get():
            """
            Get the clipboard content.
            :return: clipboard content
            :rtype: six.text_type
            """
            return _CLIPBOARD
        
        def clipboard_set(s):
            """
            Set the clipboard content.
            :param s: string to set
            :type s: six.text_type
            """
            global _CLIPBOARD
            assert isinstance(s, six.text_type)
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
        'six',
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
