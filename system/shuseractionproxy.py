# coding: utf-8
"""
Centralize handlers for various user actions.
"""

# noinspection PyAttributeOutsideInit,PyDocstring
class ShUserActionProxy(object):
    """
    The purpose of this object is to be a centralized place to respond
    to any user actions trigger from the UI including typing, touching,
    tap, etc. A centralized object makes it easier to be substituted by
    other user-defined object for command script, e.g. ssh.

    :param StaSh stash:
    """

    def __init__(self, stash):
        self.stash = stash
        self.reset()

    @property
    def vk_responder(self):
        return self._vk_responder or self.stash.ui

    @vk_responder.setter
    def vk_responder(self, value):
        self._vk_responder = value

    @property
    def tv_responder(self):
        return self._tv_responder or self.stash.terminal.tv_delegate

    @tv_responder.setter
    def tv_responder(self, value):
        self._tv_responder = value

    def reset(self):
        self._vk_responder = None
        self._tv_responder = None

    # --------------------- Proxy -----------------------------------------
    # Buttons
    def vk_tapped(self, sender):
        self.vk_responder.vk_tapped(sender)

    # TextView delegate methods
    def textview_did_begin_editing(self, sender):
        self.tv_responder.textview_did_begin_editing(sender)

    def textview_did_end_editing(self, sender):
        self.tv_responder.textview_did_end_editing(sender)

    def textview_should_change(self, sender, rng, replacement):
        return self.tv_responder.textview_should_change(sender, rng, replacement)

    def textview_did_change(self, sender):
        self.tv_responder.textview_did_change(sender)

    def textview_did_change_selection(self, sender):
        self.tv_responder.textview_did_change_selection(sender)

    # Virtual key row swipe gesture
    def scrollview_did_scroll(self, sender):
        pass

    # Keyboard shortcuts
    def keyCommands(self, modifier, key):
        pass

