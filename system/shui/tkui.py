"""
Tkinter UI for StaSh
"""
import logging


class ShUI(object):
    """
    An UI using the Tkinter module.
    """
    def __init__(self, stash, debug=False):
        self.stash = stash
        self.debug = debug
        self.logger = logging.getLogger('StaSh.UI')
