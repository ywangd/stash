"""
OS/device specific interfaces
"""
import sys

import six


IN_PYTHONISTA = sys.executable.find('Pythonista') >= 0



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
        SITE_PACKAGES_DIR_NAME = "site-packages-3"
    else:
        SITE_PACKAGES_DIR_NAME = "site-packages-2"
    SITE_PACKAGES_FOLDER_6 = "site-packages"
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
        
# ======================== DEFAULT / PC =========================
else:
    
    # ------------- clipboard --------------
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
    
    # -------------- pip ----------------------
    import site
    
    SITE_PACKAGES_FOLDER = site.getsitepackages()[0]
    SITE_PACKAGES_FOLDER_6 = None
    
    BUNDLED_MODULES = [
        'six',
    ]
