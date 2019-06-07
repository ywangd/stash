# coding: utf-8
"""
The proxy is to centralize handler dispatching for user actions
such as type, touch, swipe, key press.
"""
from contextlib import contextmanager


class ShNullResponder(object):

    def handle(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        pass

    def __getattribute__(self, item):
        return object.__getattribute__(self, 'handle')

    def __getitem__(self, item):
        return object.__getattribute__(self, 'handle')


NULL_RESPONDER = ShNullResponder()

# noinspection PyAttributeOutsideInit,PyDocstring
class ShUserActionProxy(object):
    """
    This proxy object provides a central place to register handlers for
    any user actions trigger from the UI including typing, touching,
    tap, etc. A centralized object makes it easier to substitute default
    handlers by user-defined functions in command script, e.g. ssh.

    :param StaSh stash:
    """

    def __init__(self, stash):
        self.stash = stash
        self.reset()

        # TextView delegate
        class _TVDelegate(object):
            @staticmethod
            def textview_did_begin_editing(sender):
                self.tv_responder.textview_did_begin_editing(sender)

            @staticmethod
            def textview_did_end_editing(sender):
                self.tv_responder.textview_did_end_editing(sender)

            @staticmethod
            def textview_should_change(sender, rng, replacement):
                return self.tv_responder.textview_should_change(sender, rng, replacement)

            @staticmethod
            def textview_did_change(sender):
                self.tv_responder.textview_did_change(sender)

            @staticmethod
            def textview_did_change_selection(sender):
                self.tv_responder.textview_did_change_selection(sender)

        # Virtual key row swipe gesture
        class _SVDelegate(object):
            @staticmethod
            def scrollview_did_scroll(sender):
                if self.sv_responder:
                    self.sv_responder.scrollview_did_scroll(sender)
                else:
                    sender.superview.scrollview_did_scroll(sender)

        self.tv_delegate = _TVDelegate()
        self.sv_delegate = _SVDelegate()

    # The properties are used for late binding as the various components
    # may not be ready when this class is initialized
    @property
    def vk_responder(self):
        return self._vk_responder or self.stash.ui.vk_tapped

    @vk_responder.setter
    def vk_responder(self, value):
        self._vk_responder = value

    @property
    def tv_responder(self):
        return self._tv_responder or self.stash.terminal.tv_delegate

    @tv_responder.setter
    def tv_responder(self, value):
        self._tv_responder = value

    @property
    def kc_responder(self):
        return self._kc_responder or self.stash.terminal.kc_pressed

    @kc_responder.setter
    def kc_responder(self, value):
        self._kc_responder = value

    @contextmanager
    def config(self,
               vk_responder=False,
               tv_responder=False,
               sv_responder=False,
               kc_responder=False):

        try:
            self._vk_responder = NULL_RESPONDER if vk_responder is False else vk_responder
            self._tv_responder = NULL_RESPONDER if tv_responder is False else tv_responder
            self.sv_responder = NULL_RESPONDER if sv_responder is False else sv_responder
            self.kc_responder = NULL_RESPONDER if kc_responder is False else kc_responder
            yield
        finally:
            self.reset()

    def reset(self):
        self._vk_responder = None
        self._tv_responder = None
        self.sv_responder = None
        self._kc_responder = None  # for keyCommands

    # --------------------- Proxy ---------------------
    # Buttons
    def vk_tapped(self, sender):
        self.vk_responder(sender)

    # Keyboard shortcuts
    def kc_pressed(self, key, modifierFlags):
        self.kc_responder(key, modifierFlags)

