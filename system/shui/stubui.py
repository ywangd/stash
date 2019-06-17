"""
Stub ui and terminal for testing.
"""
import six

from .base import ShBaseUI, ShBaseTerminal


class ShUI(ShBaseUI):
    """
    Stub UI for testing.
    """
    def __init__(self, *args, **kwargs):
        ShBaseUI.__init__(self, *args, **kwargs)
        self.terminal = ShTerminal(self.stash, self)
    
    def show(self):
        pass


class ShTerminal(ShBaseTerminal):
    """
    Stub terminal for testing.
    """
    def __init__(self, *args, **kwargs):
        ShBaseTerminal.__init__(self, *args, **kwargs)
        self._text = u""
    
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value):
        assert isinstance(value, six.text_type)
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
