"""
UI base classes.
"""
import ast
import logging
import time

import six

from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_CU, K_TAB, K_HIST, K_CZ, K_KB


class ShBaseUI(object):
    """
    Baseclass for the UI.
    :param stash: assoziated StaSh instance
    :type stash : StaSh
    :param debug: debug flaf
    :type debug: bool
    :param debug_terminal: debug flag for the terminal
    :type debug_terminal: bool
    """
    def __init__(self, stash, debug=False, debug_terminal=False):
        self.stash = stash
        self.debug = debug
        self.debug_terminal = debug_terminal
        self.logger = logging.getLogger('StaSh.UI')
        
        self.BUFFER_MAX = stash.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = ('Menlo-Regular', stash.config.get('display', 'TEXT_FONT_SIZE'))
        self.BUTTON_FONT = ('Menlo-Regular', stash.config.getint('display', 'BUTTON_FONT_SIZE'))
        self.vk_symbols = stash.config.get('display', 'VK_SYMBOLS')
    
    def show(self):
        """
        Show the UI.
        """
        raise NotImplementedError()
    
    def on_exit(self):
        """
        This method should be called when the UI will be closed.
        """
        # delegate task to the core
        self.stash.on_exit()
    
    # ================== key commands ========================
    
    def dummyAction(self):
        pass

    def controlCAction(self):
        self.stash.ui.vk_tapped(K_CC)

    def controlDAction(self):
        self.vk_tapped(K_CD)

    def controlPAction(self):
        self.vk_tapped(K_HUP)

    def controlNAction(self):
        self.vk_tapped(K_HDN)

    def controlKAction(self):
        self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_CURSOR_TO_END, '')

    def controlUAction(self):
        self.vk_tapped(K_CU)

    def controlAAction(self):  # Move cursor to beginning of the input
        self.stash.mini_buffer.set_cursor(0)

    def controlEAction(self):  # Move cursor to end of the input
        self.stash.mini_buffer.set_cursor(0, whence=2)

    def controlWAction(self):  # delete one word backwards
        self.stash.mini_buffer.delete_word(self.selected_range)

    def controlLAction(self):  # delete one word backwards
        self.stash.stream.feed(u'\u009bc%s' % stash.runtime.get_prompt(), no_wait=True)

    def controlZAction(self):
        self.stash.runtime.push_to_background()

    def arrowUpAction(self):
        self.vk_tapped(K_HUP)

    def arrowDownAction(self):
        self.vk_tapped(K_HDN)

    def arrowLeftAction(self):
        self.stash.mini_buffer.set_cursor(-1, whence=1)

    def arrowRightAction(self):
        self.stash.mini_buffer.set_cursor(1, whence=1)
    
    def vk_tapped(self, vk):
        """
        Called when a key was pressed
        :param vk: the pressed key
        :type vk: int
        """
        if vk == K_TAB:  # Tab completion
            rng = self.terminal.selected_range
            # Valid cursor positions are only when non-selection and after the modifiable position
            if rng[0] == rng[1] and rng[0] >= self.stash.main_screen.x_modifiable:
                self.stash.mini_buffer.feed(rng, '\t')

        elif vk == K_HIST:
            self.history_present(self.stash.runtime.history)

        elif vk == K_HUP:
            self.stash.runtime.history.up()

        elif vk == K_HDN:
            self.stash.runtime.history.down()

        elif vk == K_CD:
            if self.stash.runtime.child_thread:
                self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_BUFFER_END, '\0')

        elif vk == K_CC:
            if not self.stash.runtime.child_thread:
                self.stash.write_message('no thread to terminate\n')
                self.stash.io.write(self.stash.runtime.get_prompt())

            else:  # ctrl-c terminates the entire stack of threads
                self.stash.runtime.child_thread.kill()  # this recursively kill any nested child threads
                time.sleep(0.5)  # wait a moment for the thread to terminate

        elif vk == K_CZ:
            self.stash.runtime.push_to_background()

        elif vk == K_KB:
            if self.terminal.is_editing:
                self.terminal.end_editing()
            else:
                self.terminal.begin_editing()

        elif vk == K_CU:
            self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_MODIFIABLE_CHARS, '')


class ShBaseTerminal(object):
    """
    This is the base class for the multiline text used for bnoth in- and output.
    :param stash: assoziated StaSh instance
    :type stash: stash.stash.StaSh
    :param parent: the parent ShBaseUI
    :type parent: ShBaseUI
    """
    
    def __init__(self, stash, parent):
        self.stash = stash
        self.parent = parent
        self.debug = self.parent.debug_terminal
        self.logger = logging.getLogger('StaSh.Terminal')
        
        self.stash.terminal = self
        
        # whether the terminal cursor position is in sync with main screen
        self.cursor_synced = False
        
        self.background_color = ast.literal_eval(stash.config.get('display', 'BACKGROUND_COLOR'))
        self.font_size = stash.config.getint('display', 'TEXT_FONT_SIZE')
        self.text_color = ast.literal_eval(stash.config.get('display', 'TEXT_COLOR'))
        self.tint_color = ast.literal_eval(stash.config.get('display', 'TINT_COLOR'))

        self.indicator_style = stash.config.get('display', 'INDICATOR_STYLE')
    
    @property
    def text(self):
        """
        The text of the terminal. Unicode.
        """
        raise NotImplementedError()
    
    @text.setter
    def text(self, value):
        assert isinstance(value, six.text_type)
        raise NotImplementedError()
        
    @property
    def text_length(self):
        """
        The length of the text
        """
        return len(self.text)  # default implementation
    
    @property
    def selected_range(self):
        """
        The selected range.
        """
        raise NotImplementedError()

    @selected_range.setter
    def selected_range(self, rng):
        """
        Set the cursor selection range. Note it checks the current range first and
        only change it if the new range is different. This is to avoid setting
        unwanted cursor_synced flag. Without the check, the cursor is repositioned
        with the same range, this turn on the cursor_synced flag BUT will NOT trigger
        the did_change_selection event (which is paired to cancel the cursor_synced
        flag).
        
        Important: set self.cursor_synced = False if the above mentioned conditions are true
        """
        raise NotImplementedError()
    
    def scroll_to_end(self):
        """
        Scroll to the end of the text.
        """
        raise NotImplementedError()
    
    def set_focus(self):
        """
        Set the focus to the UI.
        This means that user keyboard inputs should be send to the terminal.
        """
        raise NotImplementedError()
    
    def lose_focus(self):
        """
        Lose the focus.
        """
        self.end_editing()
