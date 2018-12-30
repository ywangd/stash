# coding: utf-8
"""
Physical terminal is what an user sees.
"""
import ast
import logging

try:
    import ui
    from objc_util import *
except ImportError:
    from . import dummyui as ui
    from .dummyobjc_util import *

from .shcommon import CTRL_KEY_FLAG


try:
	unicode
except NameError:
	unicode = str

# ObjC related stuff
UIFont = ObjCClass('UIFont')


class ShTVDelegate(object):

    def __init__(self, stash, terminal, mini_buffer, main_screen):
        self.stash = stash
        self.terminal = terminal
        self.mini_buffer = mini_buffer
        self.main_screen = main_screen

    def textview_did_begin_editing(self, tv):
        self.terminal.is_editing = True

    def textview_did_end_editing(self, tv):
        self.terminal.is_editing = False

    def textview_should_change(self, tv, rng, replacement):
        self.mini_buffer.feed(rng, replacement)
        return False  # always false

    def textview_did_change(self, tv):
        """
        The code is a fix to a possible UI system bug:
            Some key-combos that delete texts, e.g. alt-delete, cmd-delete, from external
        keyboard do not trigger textview_should_change event. So following checks
        are added to ensure consistency between in-memory and actual UI.
        """
        rng = self.terminal.selected_range
        main_screen_text = self.main_screen.text
        terminal_text = self.terminal.text
        x_modifiable = self.main_screen.x_modifiable
        if rng[0] == rng[1] and main_screen_text[rng[0]:] != terminal_text[rng[0]:]:
            if rng[0] >= x_modifiable:
                self.mini_buffer.feed(None, main_screen_text[x_modifiable: rng[0]] + terminal_text[rng[0]:])
                self.mini_buffer.set_cursor(-len(terminal_text[rng[0]:]), whence=2)
            else:
                s = terminal_text[rng[0]:]
                self.main_screen.intact_right_bound = rng[0]  # mark the buffer to be re-rendered
                # If the trailing string is shorter than the modifiable chars,
                # this means there are valid deletion for the modifiable chars
                # and we should keep it.
                if len(s) < len(self.mini_buffer.modifiable_string):
                    self.mini_buffer.feed(None, s)
                    self.mini_buffer.set_cursor(0, whence=0)
                else:  # nothing should be deleted
                    self.mini_buffer.set_cursor(0, whence=2)

    def textview_did_change_selection(self, tv):
        # This callback was used to provide approximated support for H-Up/Dn
        # shortcuts from an external keyboard. It is no longer necessary as
        # proper external keyboard support is now possible with objc_util.

        # If cursor is in sync already, as a result of renderer call, flag it
        # to False for future checking.
        if self.terminal.cursor_synced:
            self.terminal.cursor_synced = False
        else:
            # Sync the cursor position on terminal to main screen
            # Mainly used for when user touches and changes the terminal cursor position.
            self.mini_buffer.sync_cursor(self.terminal.selected_range)


# noinspection PyAttributeOutsideInit,PyUnusedLocal,PyPep8Naming
class ShTerminal(object):

    """
    This is a wrapper class of the actual TextView that subclass the SUITextView.
    The wrapper is used to encapsulate the objc calls so that it behaves more like
    a regular ui.TextView.
    """

    def __init__(self, stash, superview, width, height, debug=False):

        self.debug = debug
        self.logger = logging.getLogger('StaSh.Terminal')

        self.stash = stash
        stash.terminal = self

        # whether the terminal cursor position is in sync with main screen
        self.cursor_synced = False

        # Create the actual TextView by subclass SUITextView
        UIKeyCommand = ObjCClass('UIKeyCommand')

        def kcDispatcher_(_self, _cmd, _sender):
            key_cmd = ObjCInstance(_sender)
            stash.user_action_proxy.kc_pressed(str(key_cmd.input()), key_cmd.modifierFlags())

        def keyCommands(_self, _cmd):
            key_commands = [
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('C', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('D', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('P', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('N', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('K', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('U', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('A', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('E', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('W', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('L', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('Z', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('[', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_(']', CTRL_KEY_FLAG, 'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputUpArrow',
                                                                       0,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputDownArrow',
                                                                       0,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputLeftArrow',
                                                                       0,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputRightArrow',
                                                                       0,
                                                                       'kcDispatcher:'),
            ]
            commands = ns(key_commands)
            return commands.ptr

        def dummyAction():
            pass

        def controlCAction():
            ui = stash.ui
            stash.ui.vk_tapped(ui.k_CC)

        def controlDAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_CD)

        def controlPAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_hup)

        def controlNAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_hdn)

        def controlKAction():
            stash.mini_buffer.feed(stash.mini_buffer.RANGE_CURSOR_TO_END, '')

        def controlUAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_CU)

        def controlAAction():  # Move cursor to beginning of the input
            stash.mini_buffer.set_cursor(0)

        def controlEAction():  # Move cursor to end of the input
            stash.mini_buffer.set_cursor(0, whence=2)

        def controlWAction():  # delete one word backwards
            stash.mini_buffer.delete_word(self.selected_range)

        def controlLAction():  # delete one word backwards
            stash.stream.feed(u'\u009bc%s' % stash.runtime.get_prompt(), no_wait=True)

        def controlZAction():
            stash.runtime.push_to_background()

        def arrowUpAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_hup)

        def arrowDownAction():
            ui = stash.ui
            ui.vk_tapped(ui.k_hdn)

        def arrowLeftAction():
            stash.mini_buffer.set_cursor(-1, whence=1)

        def arrowRightAction():
            stash.mini_buffer.set_cursor(1, whence=1)

        self.kc_handlers = {
            ('C', CTRL_KEY_FLAG): controlCAction,
            ('D', CTRL_KEY_FLAG): controlDAction,
            ('P', CTRL_KEY_FLAG): controlPAction,
            ('N', CTRL_KEY_FLAG): controlNAction,
            ('K', CTRL_KEY_FLAG): controlKAction,
            ('U', CTRL_KEY_FLAG): controlUAction,
            ('A', CTRL_KEY_FLAG): controlAAction,
            ('E', CTRL_KEY_FLAG): controlEAction,
            ('W', CTRL_KEY_FLAG): controlWAction,
            ('L', CTRL_KEY_FLAG): controlLAction,
            ('Z', CTRL_KEY_FLAG): controlZAction,
            ('[', CTRL_KEY_FLAG): dummyAction,
            (']', CTRL_KEY_FLAG): dummyAction,
            ('UIKeyInputUpArrow', 0): arrowUpAction,
            ('UIKeyInputDownArrow', 0): arrowDownAction,
            ('UIKeyInputLeftArrow', 0): arrowLeftAction,
            ('UIKeyInputRightArrow', 0): arrowRightAction,
        }

        _ShTerminal = create_objc_class('_ShTerminal', ObjCClass('SUITextView'),
                                        [keyCommands, kcDispatcher_])

        self.is_editing = False

        self.superview = superview

        self._delegate_view = ui.TextView()
        self._delegate_view.delegate = stash.user_action_proxy.tv_delegate
        self.tv_delegate = ShTVDelegate(stash, self, stash.mini_buffer, stash.main_screen)

        self.tvo = _ShTerminal.alloc().initWithFrame_(((0, 0), (width, height))).autorelease()
        self.tvo.setAutoresizingMask_(1 << 1 | 1 << 4)  # flex Width and Height
        self.content_inset = (0, 0, 0, 0)
        self.auto_content_inset = False

        self.background_color = ast.literal_eval(stash.config.get('display', 'BACKGROUND_COLOR'))
        font_size = stash.config.getint('display', 'TEXT_FONT_SIZE')
        self.default_font = UIFont.fontWithName_size_('Menlo-Regular', font_size)
        self.bold_font = UIFont.fontWithName_size_('Menlo-Bold', font_size)
        self.italic_font = UIFont.fontWithName_size_('Menlo-Italic', font_size)
        self.bold_italic_font = UIFont.fontWithName_size_('Menlo-BoldItalic', font_size)
        self.text_color = ast.literal_eval(stash.config.get('display', 'TEXT_COLOR'))
        self.tint_color = ast.literal_eval(stash.config.get('display', 'TINT_COLOR'))

        self.indicator_style = stash.config.get('display', 'INDICATOR_STYLE')
        self.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.autocorrection_type = 1
        self.spellchecking_type = 1

        # This setting helps preventing textview from jumping back to top
        self.non_contiguous_layout = False

        # Allow editing to the text attributes
        # self.editing_text_attributes = True

        ObjCInstance(self.superview).addSubview_(self.tvo)
        self.delegate = self._delegate_view

        # TextStorage
        self.tso = self.tvo.textStorage()

    @property
    def delegate(self):
        return self._delegate_view.delegate

    @delegate.setter
    @on_main_thread
    def delegate(self, value):
        self.tvo.setDelegate_(ObjCInstance(value).delegate())

    @property
    def background_color(self):
        return self._background_color

    @background_color.setter
    @on_main_thread
    def background_color(self, value):
        self._background_color = value
        r, g, b, a = ui.parse_color(value)
        self.tvo.setBackgroundColor_(UIColor.colorWithRed_green_blue_alpha_(r, g, b, 1))

    @property
    def text_font(self):
        return self._text_font

    @text_font.setter
    @on_main_thread
    def text_font(self, value):
        name, size = self._text_font = value
        self.tvo.setFont_(UIFont.fontWithName_size_(name, size))

    @property
    def indicator_style(self):
        return self.tvo.indicatorStyle()

    @indicator_style.setter
    @on_main_thread
    def indicator_style(self, value):
        choices = {
            'default': 0,
            'black': 1,
            'white': 2,
        }
        self.tvo.setIndicatorStyle_(choices[value])

    @property
    def text_color(self):
        return self._text_color

    @text_color.setter
    @on_main_thread
    def text_color(self, value):
        self._text_color = value
        r, g, b, a = ui.parse_color(value)
        self.tvo.setTextColor_(UIColor.colorWithRed_green_blue_alpha_(r, g, b, 1))

    @property
    def tint_color(self):
        return self._tint_color

    @tint_color.setter
    @on_main_thread
    def tint_color(self, value):
        self._tint_color = value
        r, g, b, a = ui.parse_color(value)
        self.tvo.setTintColor_(UIColor.colorWithRed_green_blue_alpha_(r, g, b, 1))

    @property
    def text(self):
        return unicode(self.tvo.text())

    @text.setter
    @on_main_thread
    def text(self, value):
        self.tvo.setText_(value)

    @property
    def text_length(self):
        return self.tvo.text().length()

    @property
    def attributed_text(self):
        return self.tvo.attributedText()

    @attributed_text.setter
    @on_main_thread
    def attributed_text(self, value):
        self.tvo.setAttributedText_(value)

    @property
    def selected_range(self):
        nsrange = self.tvo.selectedRange()
        return nsrange.location, nsrange.location + nsrange.length

    @selected_range.setter
    @on_main_thread
    def selected_range(self, rng):
        """
        Set the cursor selection range. Note it checks the current range first and
        only change it if the new range is different. This is to avoid setting
        unwanted cursor_synced flag. Without the check, the cursor is repositioned
        with the same range, this turn on the cursor_synced flag BUT will NOT trigger
        the did_change_selection event (which is paired to cancel the cursor_synced
        flag).
        """
        if self.selected_range != rng:
            self.cursor_synced = True
            self.tvo.setSelectedRange_((rng[0], rng[1] - rng[0]))

    @property
    def autocapitalization_type(self):
        return self._autocapitalization_type

    @autocapitalization_type.setter
    @on_main_thread
    def autocapitalization_type(self, value):
        self._autocapitalization_type = value
        self.tvo.performSelector_withObject_('setAutocapitalizationType:', value)

    @property
    def autocorrection_type(self):
        return self._autocorrection_type

    @autocorrection_type.setter
    @on_main_thread
    def autocorrection_type(self, value):
        self._autocorrection_type = value
        ObjCInstanceMethod(self.tvo, 'setAutocorrectionType:')(value)

    @property
    def spellchecking_type(self):
        return self._spellchecking_type

    @spellchecking_type.setter
    @on_main_thread
    def spellchecking_type(self, value):
        self._spellchecking_type = value
        self.tvo.performSelector_withObject_('setSpellCheckingType:', value)

    @property
    def content_inset(self):
        return self._content_inset

    @content_inset.setter
    @on_main_thread
    def content_inset(self, value):
        self._content_inset = value
        insetStructure = self.tvo.contentInset()
        insetStructure.top, insetStructure.left, insetStructure.bottom, insetStructure.right = value

    @property
    def auto_content_inset(self):
        return self._auto_content_inset

    @auto_content_inset.setter
    @on_main_thread
    def auto_content_inset(self, value):
        self._auto_content_inset = value
        self.tvo.setAutomaticallyAdjustsContentInsetForKeyboard_(value)

    @property
    def non_contiguous_layout(self):
        return self._non_contiguous_layout

    @non_contiguous_layout.setter
    @on_main_thread
    def non_contiguous_layout(self, value):
        self._non_contiguous_layout = value
        self.tvo.layoutManager().setAllowsNonContiguousLayout_(value)

    @property
    def editing_text_attributes(self):
        return self._editing_text_attributes

    @editing_text_attributes.setter
    @on_main_thread
    def editing_text_attributes(self, value):
        self._editing_text_attributes = value
        self.tvo.setAllowsEditingTextAttributes_(value)

    @on_main_thread
    def scroll_range_to_visible(self, rng):
        self.tvo.scrollRangeToVisible_(rng)

    @property
    def size(self):
        size = self.tvo.size()
        return size.width, size.height

    @size.setter
    @on_main_thread
    def size(self, value):
        """
        Set the width and height of the view
        :param value: A tuple of (width, height)
        """
        self.tvo.setSize_(value)

    @property
    def content_size(self):
        size = self.tvo.contentSize()
        return size.width, size.height

    @property
    def content_offset(self):
        point = self.tvo.contentOffset()
        return point.x, point.y

    @property
    def visible_rect(self):
        rect = self.tvo.visibleRect()
        return rect.size.width, rect.size.height, rect.origin.x, rect.origin.y

    @on_main_thread
    def scroll_to_end(self):
        content_height = self.content_size[1]
        # rect_height is the visible rect's height
        # rect_y is the y location where the visible rect locates in the
        # coordinate of content_size
        _, rect_height, _, rect_y = self.visible_rect
        # If the space below rect_y is more than the visible rect's height,
        # or if the visible rect is over-scrolled, scroll to the last line.
        if content_height - rect_y > rect_height or \
                (content_height > rect_height > content_height - rect_y):  # over-scroll
            self.tvo.scrollRangeToVisible_((len(self.text), 0))

    @on_main_thread
    def begin_editing(self):
        self.tvo.becomeFirstResponder()

    @on_main_thread
    def end_editing(self):
        self.tvo.resignFirstResponder()

    # noinspection PyCallingNonCallable
    def kc_pressed(self, key, modifierFlags):
        handler = self.kc_handlers.get((key, modifierFlags), None)
        if handler:
            handler()


class StubTerminal(ObjCClass):

    def __init__(self, stash, *args, **kwargs):
        self.stash = stash
        stash.terminal = self
        self.text = ''
        super(StubTerminal, self).__init__(*args, **kwargs)