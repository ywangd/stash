"""
Stub ui and terminal for testing.
"""

import six

from .base import ShBaseUI, ShBaseTerminal, ShBaseSequentialRenderer


class ShUI(ShBaseUI):
    """
    Stub UI for testing.
    """

    def __init__(self, *args, **kwargs):
        ShBaseUI.__init__(self, *args, **kwargs)
        self.terminal = ShTerminal(self.stash, self)

    def show(self):
        pass

    def close(self):
        self.on_exit()


class ShTerminal(ShBaseTerminal):
    """
    Stub terminal for testing.
    """

    def __init__(self, *args, **kwargs):
        ShBaseTerminal.__init__(self, *args, **kwargs)
        self._text = ""

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        assert isinstance(value, (six.text_type, six.binary_type))
        self._text = value

    @property
    def selected_range(self):
        # always at the end
        return (self.text_length, self.text_length)

    @selected_range.setter
    def selected_range(self, value):
        raise NotImplementedError()

    @property
    def text_length(self):
        return len(self.text)  # default implementation

    def scroll_to_end(self):
        pass

    def set_focus(self):
        pass

    def lose_focus(self):
        pass

    def get_wh(self):
        return (80, 24)


class ShSequentialRenderer(ShBaseSequentialRenderer):
    """
    Stub renderer for testing
    """

    def render(self, no_wait=False):
        # Lock screen to get atomic information
        with self.screen.acquire_lock():
            intact_left_bound, intact_right_bound = self.screen.get_bounds()
            screen_buffer_length = self.screen.text_length
            cursor_xs, cursor_xe = self.screen.cursor_x
            renderable_chars = self.screen.renderable_chars
            self.screen.clean()

        self.terminal.text = self.screen.text
