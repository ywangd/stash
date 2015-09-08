# coding: utf-8
import ast
import logging

try:
    import ui
    import console
except ImportError:
    import dummyui as ui
    import dummyconsole as console

try:
    from objc_util import *
except ImportError:
    from .dummyobjc_util import *

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
                if len(s) < len(self.mini_buffer.modifiable_chars):
                    self.mini_buffer.feed(None, s)
                    self.mini_buffer.set_cursor(0, whence=0)
                else:  # nothing should be deleted
                    self.mini_buffer.set_cursor(0, whence=2)

    def textview_did_change_selection(self, tv):
        # This callback was used to provide approximated support for H-Up/Dn
        # shortcuts from an external keyboard. It is no longer necessary as
        # proper external keyboard support is now possible with objc_util.
        pass


# noinspection PyAttributeOutsideInit
class ShTerminal(object):

    """
    This is a wrapper class of the actual TextView that subclass the SUITextView.
    The wrapper is used to encapsulate the objc calls so that it behaves more like
    a regular ui.TextView.
    """

    def __init__(self, stash, superview, width, height, debug=False):

        self.stash = stash
        stash.terminal = self

        # Create the actual TextView by subclass SUITextView
        UIKeyCommand = ObjCClass('UIKeyCommand')

        def keyCommands(_self, _cmd):
            ctrl_key_flag = (1 << 18)  # Control key
            cmd_key_flag = (1 << 20)  # Command key
            key_commands = [
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('C', ctrl_key_flag, 'controlCAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('D', ctrl_key_flag, 'controlDAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('P', ctrl_key_flag, 'controlPAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('N', ctrl_key_flag, 'controlNAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('U', ctrl_key_flag, 'controlUAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('A', ctrl_key_flag, 'controlAAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('E', ctrl_key_flag, 'controlEAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('W', ctrl_key_flag, 'controlWAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputUpArrow',
                                                                       0,
                                                                       'arrowUpAction'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('UIKeyInputDownArrow',
                                                                       0,
                                                                       'arrowDownAction'),
            ]
            commands = ns(key_commands)
            return commands.ptr

        def controlCAction(_self, _cmd):
            # selfo = ObjCInstance(_self)
            ui = stash.ui
            ui.vk_tapped(ui.k_CC)

        def controlDAction(_self, _cmd):
            ui = stash.ui
            ui.vk_tapped(ui.k_CD)

        def controlPAction(_self, _cmd):
            ui = stash.ui
            ui.vk_tapped(ui.k_hup)

        def controlNAction(_self, _cmd):
            ui = stash.ui
            ui.vk_tapped(ui.k_hdn)

        def controlUAction(_self, _cmd):
            ui =stash.ui
            ui.vk_tapped(ui.k_CU)

        def controlAAction(_self, _cmd):  # Move cursor to beginning of the input
            stash.mini_buffer.set_cursor(0)

        def controlEAction(_self, _cmd):  # Move cursor to end of the input
            stash.mini_buffer.set_cursor(0, whence=2)

        def controlWAction(_self, _cmd):  # delete one word backwards
            stash.mini_buffer.delete_word(self.selected_range)

        def arrowUpAction(_self, _cmd):
            ui = stash.ui
            ui.vk_tapped(ui.k_hup)

        def arrowDownAction(_self, _cmd):
            ui = stash.ui
            ui.vk_tapped(ui.k_hdn)

        _ShTerminal = create_objc_class('_ShTerminal', ObjCClass('SUITextView'),
                                        [keyCommands,
                                         controlCAction, controlDAction,
                                         controlPAction, controlNAction,
                                         controlUAction, controlAAction, controlEAction,
                                         controlWAction,
                                         arrowUpAction, arrowDownAction])

        self.is_editing = False

        self.superview = superview
        self.debug = debug
        self.logger = logging.getLogger('StaSh.Terminal')

        self._delegate_view = ui.TextView()
        self._delegate_view.delegate = ShTVDelegate(stash, self, stash.mini_buffer, stash.main_screen)

        self.tvo = _ShTerminal.alloc().initWithFrame_(((0, 0), (width, height)))
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
        r, g, b = self._background_color = value
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
        r, g, b = self._text_color = value
        self.tvo.setTextColor_(UIColor.colorWithRed_green_blue_alpha_(r, g, b, 1))

    @property
    def tint_color(self):
        return self._tint_color

    @tint_color.setter
    @on_main_thread
    def tint_color(self, value):
        r, g, b = self._tint_color = value
        self.tvo.setTintColor_(UIColor.colorWithRed_green_blue_alpha_(r, g, b, 1))

    @property
    def text(self):
        return str(self.tvo.text())

    @text.setter
    @on_main_thread
    def text(self, value):
        self.tvo.setText_(value)

    @property
    def selected_range(self):
        nsrange = self.tvo.selectedRange()
        return nsrange.location, nsrange.location + nsrange.length

    @selected_range.setter
    @on_main_thread
    def selected_range(self, rng):
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
        self.tvo.performSelector_withObject_('setAutocorrectionType:', value)

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
    def content_size(self):
        size = self.tvo.contentSize()
        return size.width, size.height

    @property
    def size(self):
        size = self.tvo.size()
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


class StubTerminal(ObjCClass):

    def __init__(self, stash, *args, **kwargs):
        self.stash = stash
        stash.terminal = self
        self.text = ''
        super(StubTerminal, self).__init__(*args, **kwargs)
