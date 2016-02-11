# coding: utf-8
"""

"""


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

    def vk_tapped(self, sender):
        """
        Handle button press
        :param vk:
        :return:
        """
        pass

    def history_popover_tapped(self, sender):
        """
        Handle tapping on history popover list
        :param sender:
        :return:
        """
        pass

    # TextView delegate methods
    def textview_did_begin_editing(self, sender):
        pass

    def textview_did_end_editing(self, sender):
        pass

    def textview_should_change(self, sender):
        pass

    def textview_did_change(self, sender):
        pass

    def textview_did_change_selection(self, sender):
        pass

    # Virtual key row swipe gesture
    def scrollview_did_scroll(self, sender):
        pass

    # Keyboard shortcuts
    def keyCommands(self, modifier, key):
        pass

