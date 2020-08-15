"""
tests for the tkui
"""
import logging

from unittest import skipIf

from stash.tests.stashtest import StashTestCase

try:
    from stash.system.shui.tkui import ShTerminal
except ImportError:
    ShTerminal = None



class NoInitTkTerminal(ShTerminal):
    """
    Subclass of ShTerminal which does not initiate the superclass
    """
    def __init__(self, text=u""):
        self._text = ""
        self.text = text
        self.logger = logging.getLogger('StaSh.Terminal')
    
    @property
    def text(self):
        return self._text
    
    @text.setter
    def text(self, value):
        self._text = value


@skipIf(ShTerminal is None, "No Tk-GUI available")
class TkTerminalTests(StashTestCase):
    """
    Tests for stash.system.shui.tkui.ShTerminal
    """
    tc = NoInitTkTerminal
    
    def test_tk_index_conversion(self):
        """
        Test conversion to and from a tk index to a tuple
        """
        values = {  # tk index -> expected
            "1.0": (0, 0),
            "1.1": (0, 1),
            "2.0": (1, 0),
            "2.2": (1, 2),
            "10.11": (9, 11),
            "9.2": (8, 2),
        }
        terminal = self.tc()
        for tki in values:
            expected = values[tki]
            converted = terminal._tk_index_to_tuple(tki)
            self.assertEqual(converted, expected)
            # convert back
            back = terminal._tuple_to_tk_index(converted)
            self.assertEqual(back, tki)
    
    def test_abs_rel_conversion_1(self):
        """
        First test for conversion of absolute and relative indexes
        """
        s = """0123
567
9
"""
        values = {  # rel -> abs
            0: (0, 0),
            1: (0, 1),
            2: (0, 2),
            3: (0, 3),
            4: (0, 4),
            5: (1, 0),
            6: (1, 1),
            7: (1, 2),
            8: (1, 3),
            9: (2, 0),
            10: (2, 1),
        }
        terminal = self.tc(s)
        for rel in values:
            expected = values[rel]
            ab = terminal._rel_cursor_pos_to_abs_pos(rel)
            self.assertEqual(ab, expected)
            # convert back
            back = terminal._abs_cursor_pos_to_rel_pos(ab)
            self.assertEqual(back, rel)
