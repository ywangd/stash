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

