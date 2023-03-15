# coding: utf-8
from time import time

import six

import ui
from objc_util import on_main_thread, ObjCInstanceMethod, UIColor, create_objc_class, ObjCClass, ObjCInstance, ns

from ..shcommon import ON_IPAD, ON_IOS_8, sh_delay
from ..shcommon import K_CC, K_CD, K_HUP, K_HDN, K_CU, K_TAB, K_HIST, K_CZ, K_KB, CTRL_KEY_FLAG
from ..shscreens import DEFAULT_CHAR, ShChar
from .base import ShBaseUI, ShBaseTerminal, ShBaseSequentialRenderer

try:
    from objc_util import *
except ImportError:
    from .dummyobjc_util import *


NSMutableAttributedString = ObjCClass('NSMutableAttributedString')
UIFont = ObjCClass('UIFont')

BlackColor = UIColor.blackColor()
RedColor = UIColor.redColor()
GreenColor = UIColor.greenColor()
BrownColor = UIColor.brownColor()
BlueColor = UIColor.blueColor()
# BlueColor = UIColor.colorWithRed_green_blue_alpha_(0.3, 0.3, 1.0, 1.0)
MagentaColor = UIColor.magentaColor()
CyanColor = UIColor.cyanColor()
WhiteColor = UIColor.whiteColor()
GrayColor = UIColor.grayColor()
# GrayColor = UIColor.colorWithRed_green_blue_alpha_(0.5, 0.5, 0.5, 1.0)
YellowColor = UIColor.yellowColor()
# SmokeColor = UIColor.smokeColor()
SmokeColor = UIColor.colorWithRed_green_blue_alpha_(0.8, 0.8, 0.8, 1.0)


class ShVk(ui.View):
    """
    The virtual keyboard container, which implements a swipe cursor positioning gesture

    :type stash : StaSh
    """

    def __init__(self, stash, name='vks', flex='wh'):
        self.stash = stash
        self.flex = flex
        self.name = name
        self.sv = ui.ScrollView(name, flex='wh')
        super(ShVk, self).add_subview(self.sv)
        self.sv.delegate = self
        self.dx = 0
        self.SCROLL_PER_CHAR = 20.0  # Number of pixels to scroll to move 1 character

    def layout(self):
        self.sv.content_size = (self.width + 1, self.height)

    def add_subview(self, subview):
        self.sv.add_subview(subview)

    def remove_subview(self, subview):
        self.sv.remove_subview(subview)

    def scrollview_did_scroll(self, scrollview):
        # integrate small scroll motions, but keep scrollview from actually moving
        if not scrollview.decelerating:
            self.dx -= scrollview.content_offset[0] / self.SCROLL_PER_CHAR
        scrollview.content_offset = (0.0, 0.0)

        offset = int(self.dx)
        if offset:
            self.dx -= offset
            self.stash.mini_buffer.set_cursor(offset, whence=1)


class ShUI(ShBaseUI, ui.View):
    """
    UI using the pythonista ui module
    """

    def __init__(self, *args, **kwargs):

        ShBaseUI.__init__(self, *args, **kwargs)

        self.is_editing = False

        # Start constructing the view's layout
        self.name = 'StaSh'
        self.flex = 'WH'
        self.background_color = 0.0

        self.txts = ui.View(name='txts', flex='WH')  # Wrapper view of output and input areas
        self.add_subview(self.txts)
        self.txts.background_color = 0.7

        # TODO: The accessory keys can be moved to a separate class
        self.vks = ShVk(self.stash, name='vks', flex='WT')
        self.vks.sv.delegate = self.stash.user_action_proxy.sv_delegate
        self.txts.add_subview(self.vks)
        self.vks.background_color = 0.7

        k_hspacing = 1

        self.k_tab = ui.Button(name='k_tab', title=' Tab ', flex='TB')
        self.vks.add_subview(self.k_tab)
        self.k_tab.action = self._vk_tapped
        self.k_tab.font = self.BUTTON_FONT
        self.k_tab.border_width = 1
        self.k_tab.border_color = 0.9
        self.k_tab.corner_radius = 5
        self.k_tab.tint_color = 'black'
        self.k_tab.background_color = 'white'
        self.k_tab.size_to_fit()

        self.k_grp_0 = ShVk(self.stash, name='k_grp_0', flex='WT')  # vk group 0
        self.k_grp_0.sv.delegate = self._vk_tapped
        self.vks.add_subview(self.k_grp_0)
        self.k_grp_0.background_color = 0.7
        self.k_grp_0.x = self.k_tab.width + k_hspacing

        self.k_hist = ui.Button(name='k_hist', title=' H ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hist)
        self.k_hist.action = self._vk_tapped
        self.k_hist.font = self.BUTTON_FONT
        self.k_hist.border_width = 1
        self.k_hist.border_color = 0.9
        self.k_hist.corner_radius = 5
        self.k_hist.tint_color = 'black'
        self.k_hist.background_color = 'white'
        self.k_hist.size_to_fit()

        self.k_hup = ui.Button(name='k_hup', title=' Up ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hup)
        self.k_hup.action = self._vk_tapped
        self.k_hup.font = self.BUTTON_FONT
        self.k_hup.border_width = 1
        self.k_hup.border_color = 0.9
        self.k_hup.corner_radius = 5
        self.k_hup.tint_color = 'black'
        self.k_hup.background_color = 'white'
        self.k_hup.size_to_fit()
        self.k_hup.x = self.k_hist.width + k_hspacing

        self.k_hdn = ui.Button(name='k_hdn', title=' Dn ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hdn)
        self.k_hdn.action = self._vk_tapped
        self.k_hdn.font = self.BUTTON_FONT
        self.k_hdn.border_width = 1
        self.k_hdn.border_color = 0.9
        self.k_hdn.corner_radius = 5
        self.k_hdn.tint_color = 'black'
        self.k_hdn.background_color = 'white'
        self.k_hdn.size_to_fit()
        self.k_hdn.x = self.k_hup.x + self.k_hup.width + k_hspacing

        self.k_CD = ui.Button(name='k_CD', title=' CD ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CD)
        self.k_CD.action = self._vk_tapped
        self.k_CD.font = self.BUTTON_FONT
        self.k_CD.border_width = 1
        self.k_CD.border_color = 0.9
        self.k_CD.corner_radius = 5
        self.k_CD.tint_color = 'black'
        self.k_CD.background_color = 'white'
        self.k_CD.size_to_fit()
        self.k_CD.x = self.k_hdn.x + self.k_hdn.width + k_hspacing

        self.k_CC = ui.Button(name='k_CC', title=' CC ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CC)
        self.k_CC.action = self._vk_tapped
        self.k_CC.font = self.BUTTON_FONT
        self.k_CC.border_width = 1
        self.k_CC.border_color = 0.9
        self.k_CC.corner_radius = 5
        self.k_CC.tint_color = 'black'
        self.k_CC.background_color = 'white'
        self.k_CC.size_to_fit()
        self.k_CC.x = self.k_CD.x + self.k_CD.width + k_hspacing

        # Kill line key
        self.k_CU = ui.Button(name='k_CU', title=' CU ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CU)
        self.k_CU.action = self._vk_tapped
        self.k_CU.font = self.BUTTON_FONT
        self.k_CU.border_width = 1
        self.k_CU.border_color = 0.9
        self.k_CU.corner_radius = 5
        self.k_CU.tint_color = 'black'
        self.k_CU.background_color = 'white'
        self.k_CU.size_to_fit()
        self.k_CU.x = self.k_CC.x + self.k_CC.width + k_hspacing

        # BG key
        self.k_CZ = ui.Button(name='k_CZ', title=' CZ ', flex='RTB')
        self.k_grp_0.add_subview(self.k_CZ)
        self.k_CZ.action = self._vk_tapped
        self.k_CZ.font = self.BUTTON_FONT
        self.k_CZ.border_width = 1
        self.k_CZ.border_color = 0.9
        self.k_CZ.corner_radius = 5
        self.k_CZ.tint_color = 'black'
        self.k_CZ.background_color = 'white'
        self.k_CZ.size_to_fit()
        self.k_CZ.x = self.k_CU.x + self.k_CU.width + k_hspacing

        # End Editing key
        self.k_KB = ui.Button(name='k_KB', title=' KB ', flex='RTB')
        self.k_grp_0.add_subview(self.k_KB)
        self.k_KB.action = self._vk_tapped
        self.k_KB.font = self.BUTTON_FONT
        self.k_KB.border_width = 1
        self.k_KB.border_color = 0.9
        self.k_KB.corner_radius = 5
        self.k_KB.tint_color = 'black'
        self.k_KB.background_color = 'white'
        self.k_KB.size_to_fit()
        self.k_KB.x = self.k_CZ.x + self.k_CZ.width + k_hspacing

        self.k_swap = ui.Button(name='k_swap', title='..', flex='LTB')
        self.vks.add_subview(self.k_swap)
        # self.k_swap.action = self.stash.user_action_proxy.vk_tapped
        self.k_swap.action = lambda sender: self.toggle_k_grp()
        self.k_swap.font = self.BUTTON_FONT
        self.k_swap.border_width = 1
        self.k_swap.border_color = 0.9
        self.k_swap.corner_radius = 5
        self.k_swap.tint_color = 'black'
        self.k_swap.background_color = 'white'
        self.k_swap.size_to_fit()
        self.k_swap.width -= 2
        self.k_swap.x = self.vks.width - self.k_swap.width

        self.k_grp_1 = ShVk(self.stash, name='k_grp_1', flex='WT')  # vk group 1
        self.k_grp_1.sv.delegate = self.stash.user_action_proxy.sv_delegate
        self.vks.add_subview(self.k_grp_1)
        self.k_grp_1.background_color = 0.7
        self.k_grp_1.x = self.k_tab.width + k_hspacing

        offset = 0
        for i, sym in enumerate(self.vk_symbols):
            if sym == ' ':
                continue
            if not ON_IPAD and i > 7:
                break

            k_sym = ui.Button(name='k_sym', title=' %s ' % sym, flex='RTB')
            self.k_grp_1.add_subview(k_sym)
            k_sym.action = lambda vk: self.stash.mini_buffer.feed(self.terminal.selected_range, vk.title.strip())
            k_sym.font = self.BUTTON_FONT
            k_sym.border_width = 1
            k_sym.border_color = 0.9
            k_sym.corner_radius = 5
            k_sym.tint_color = 'black'
            k_sym.background_color = 'white'
            k_sym.size_to_fit()
            k_sym.x = offset + k_hspacing * i
            offset += k_sym.width

        self.k_grp_0.width = self.vks.width - self.k_tab.width - self.k_swap.width - 2 * k_hspacing
        self.k_grp_1.width = self.vks.width - self.k_tab.width - self.k_swap.width - 2 * k_hspacing

        self.vks.height = self.k_hist.height
        self.vks.y = self.vks.superview.height - (self.vks.height + 4)

        self.k_grp_1.send_to_back()
        self.on_k_grp = 0

        self.terminal = ShTerminal(
            self.stash,
            self,
            self.txts,
            width=self.txts.width,
            height=self.txts.height - (self.vks.height + 8)
        )

    def keyboard_frame_did_change(self, frame):
        """
        This is needed to make sure the extra key row is not covered by the
        keyboard frame when it pops up.
        :param frame:
        :return:
        """
        if self.on_screen:
            if frame[3] > 0:  # when keyboard appears
                self.vks.hidden = False
                self.txts.height = self.height - frame[3]
                # Leave space for the virtual key row
                self.terminal.size = self.txts.width, self.txts.height - (self.vks.height + 8)
            else:  # when keyboard goes away
                # hide the virtual key row as well
                self.vks.hidden = True
                self.txts.height = self.height
                # Take all space as virtual key row is now hidden
                self.terminal.size = self.txts.width, self.txts.height
            # TODO: Scroll to end? may not be necessary
    
    def show(self):
        """
        Present the UI
        """
        self.present("panel")
        self.terminal.begin_editing()
    
    def close(self):
        ui.View.close(self)
        # on_exit() will be called in will_close()
        # TODO: check the above

    def will_close(self):
        """
        Save stuff here
        """
        self.on_exit()

    def toggle_k_grp(self):
        if self.on_k_grp == 0:
            self.k_grp_1.bring_to_front()
        else:
            self.k_grp_0.bring_to_front()
        self.on_k_grp = 1 - self.on_k_grp

    def history_present(self, history):
        """
        Present a history popover.
        :param history: history to present
        :type history: ShHistory
        """
        listsource = ui.ListDataSource(history.getlist())
        listsource.action = self.history_popover_tapped
        table = ui.TableView()
        listsource.font = self.BUTTON_FONT
        table.data_source = listsource
        table.delegate = listsource
        table.width = 300
        table.height = 300
        table.row_height = self.BUTTON_FONT[1] + 4
        table.present('popover')
        table.wait_modal()

    def history_popover_tapped(self, sender):
        """
        Called when a row in the history popover was tapped.
        :param sender: sender of the event
        :type sender: ui.TableView
        """
        if sender.selected_row >= 0:
            self.history_selected(sender.items[sender.selected_row], sender.selected_row)
    
    def _vk_tapped(self, sender):
        """
        Called when a key was tapped
        :param sender: sender of the event
        :type sender: ui.Button
        """
        # resolve key
        mapping = [
            # we can not use a dict here because ui.Button is unhashable
            # instead, we use a pair of (key, value) and apply a liner search
            # a binary search may be more efficient, but come on, this is definetly not required here
            (self.k_tab, K_TAB),
            (self.k_hist, K_HIST),
            (self.k_hup, K_HUP),
            (self.k_hdn, K_HDN),
            (self.k_CC, K_CC),
            (self.k_CD, K_CD),
            (self.k_CU, K_CU),
            (self.k_CZ, K_CZ),
            (self.k_KB, K_KB),
        ]
        key = None
        for k, v in mapping:
            if sender is k:
                key = v
        if key is None:
            raise ValueError("Unknown sender: " + repr(sender))
        
        # call action
        self.stash.user_action_proxy.vk_tapped(key)

# ObjC related stuff
UIFont = ObjCClass('UIFont')


# noinspection PyAttributeOutsideInit,PyUnusedLocal,PyPep8Naming
class ShTerminal(ShBaseTerminal):
    """
    This is a wrapper class of the actual TextView that subclass the SUITextView/SUITextView_PY3.
    The wrapper is used to encapsulate the objc calls so that it behaves more like
    a regular ui.TextView.
    """

    def __init__(self, stash, parent, superview, width, height):

        # Create the actual TextView by subclass SUITextView/SUITextView_PY3
        UIKeyCommand = ObjCClass('UIKeyCommand')

        def kcDispatcher_(_self, _cmd, _sender):
            key_cmd = ObjCInstance(_sender)
            stash.user_action_proxy.kc_pressed(str(key_cmd.input()), key_cmd.modifierFlags())

        def keyCommands(_self, _cmd):
            key_commands = [
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('C',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('D',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('P',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('N',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('K',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('U',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('A',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('E',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('W',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('L',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('Z',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_('[',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
                UIKeyCommand.keyCommandWithInput_modifierFlags_action_(']',
                                                                       CTRL_KEY_FLAG,
                                                                       'kcDispatcher:'),
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


        self.kc_handlers = {
            ('C',
             CTRL_KEY_FLAG): parent.controlCAction,
            ('D',
             CTRL_KEY_FLAG): parent.controlDAction,
            ('P',
             CTRL_KEY_FLAG): parent.controlPAction,
            ('N',
             CTRL_KEY_FLAG): parent.controlNAction,
            ('K',
             CTRL_KEY_FLAG): parent.controlKAction,
            ('U',
             CTRL_KEY_FLAG): parent.controlUAction,
            ('A',
             CTRL_KEY_FLAG): parent.controlAAction,
            ('E',
             CTRL_KEY_FLAG): parent.controlEAction,
            ('W',
             CTRL_KEY_FLAG): parent.controlWAction,
            ('L',
             CTRL_KEY_FLAG): parent.controlLAction,
            ('Z',
             CTRL_KEY_FLAG): parent.controlZAction,
            ('[',
             CTRL_KEY_FLAG): parent.dummyAction,
            (']',
             CTRL_KEY_FLAG): parent.dummyAction,
            ('UIKeyInputUpArrow', 0):    parent.arrowUpAction,
            ('UIKeyInputDownArrow', 0):  parent.arrowDownAction,
            ('UIKeyInputLeftArrow', 0):  parent.arrowLeftAction,
            ('UIKeyInputRightArrow', 0): parent.arrowRightAction,
        }

        try:
            _ShTerminal = create_objc_class('_ShTerminal', ObjCClass('SUITextView'), [keyCommands, kcDispatcher_])
        except ValueError:
            _ShTerminal = create_objc_class('_ShTerminal', ObjCClass('SUITextView_PY3'), [keyCommands, kcDispatcher_])

        self.is_editing = False

        self.superview = superview

        self._delegate_view = ui.TextView()
        self._delegate_view.delegate = stash.user_action_proxy.tv_delegate

        self.tvo = _ShTerminal.alloc().initWithFrame_(((0, 0), (width, height))).autorelease()
        self.tvo.setAutoresizingMask_(1 << 1 | 1 << 4)  # flex Width and Height
        self.content_inset = (0, 0, 0, 0)
        self.auto_content_inset = False

        # This setting helps preventing textview from jumping back to top
        self.non_contiguous_layout = False

        # Allow editing to the text attributes
        # self.editing_text_attributes = True

        ObjCInstance(self.superview).addSubview_(self.tvo)
        self.delegate = self._delegate_view

        # TextStorage
        self.tso = self.tvo.textStorage()
        
        # init baseclass and set attributes depending on settings
        # we have to do this this late because setting a few of these attributes requires self.tvo to be set
        ShBaseTerminal.__init__(self, stash, parent)
        
        self.default_font = UIFont.fontWithName_size_('Menlo-Regular', self.font_size)
        self.bold_font = UIFont.fontWithName_size_('Menlo-Bold', self.font_size)
        self.italic_font = UIFont.fontWithName_size_('Menlo-Italic', self.font_size)
        self.bold_italic_font = UIFont.fontWithName_size_('Menlo-BoldItalic', self.font_size)
        
        self.autocapitalization_type = ui.AUTOCAPITALIZE_NONE
        self.autocorrection_type = 1
        self.spellchecking_type = 1

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
        return six.text_type(self.tvo.text())

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
    
    def set_focus(self):
        self.begin_editing()
    
    def lose_focus(self):
        self.end_editing()

    # noinspection PyCallingNonCallable
    def kc_pressed(self, key, modifierFlags):
        handler = self.kc_handlers.get((key, modifierFlags), None)
        if handler:
            handler()
    
    def get_wh(self):
        font_width, font_height = ui.measure_string(
            'a',
            font=('Menlo-Regular', self.stash.config.getint('display', 'TEXT_FONT_SIZE')))
        w = int(self.stash.ui.width / font_width)
        h = int(self.stash.ui.height / font_height)
        return (w, h)


class ShSequentialRenderer(ShBaseSequentialRenderer):
    """
    A specific renderer for `ShSequentialScreen`. It does its job by
    building texts from the in-memory screen and insert them to the
    UI terminal.

    :param ShSequentialScreen screen: In memory screen
    :param ShTerminal terminal: The real UI terminal
    """
    FG_COLORS = {
        'black': BlackColor,
        'red': RedColor,
        'green': GreenColor,
        'brown': BrownColor,
        'blue': BlueColor,
        'magenta': MagentaColor,
        'cyan': CyanColor,
        'white': WhiteColor,
        'gray': GrayColor,
        'yellow': YellowColor,
        'smoke': SmokeColor,
        'default': WhiteColor,
    }

    BG_COLORS = {
        'black': BlackColor,
        'red': RedColor,
        'green': GreenColor,
        'brown': BrownColor,
        'blue': BlueColor,
        'magenta': MagentaColor,
        'cyan': CyanColor,
        'white': WhiteColor,
        'gray': GrayColor,
        'yellow': YellowColor,
        'smoke': SmokeColor,
        'default': BlackColor,
    }

    RENDER_INTERVAL = 0.1
    
    def __init__(self, *args, **kwargs):
        ShBaseSequentialRenderer.__init__(self, *args, **kwargs)
        self.last_rendered_time = 0
        self.render_thread = None

    def _get_font(self, attrs):
        if attrs.bold and attrs.italics:
            return self.terminal.bold_italic_font
        elif attrs.bold:
            return self.terminal.bold_font
        elif attrs.italics:
            return self.terminal.italic_font
        else:
            return self.terminal.default_font

    def _build_attributes(self, attrs):
        return {
            'NSColor': self.FG_COLORS.get(attrs.fg,
                                          WhiteColor),
            'NSBackgroundColor': self.BG_COLORS.get(attrs.bg,
                                                    BlackColor),
            'NSFont': self._get_font(attrs),
            'NSUnderline': 1 if attrs.underscore else 0,
            'NSStrikethrough': 1 if attrs.strikethrough else 0,
        }

    def _build_attributed_string(self, chars):
        """
        Build attributed text in a more efficient way than char by char.
        It groups characters with the same attributes and apply the attributes
        to them at once.
        :param [ShChar] chars: A list of ShChar upon which the attributed text is built.
        :rtype: object
        """
        # Initialize a string with default attributes
        attributed_text = NSMutableAttributedString.alloc().initWithString_attributes_(
            ''.join(char.data for char in chars),
            self._build_attributes(DEFAULT_CHAR),
        ).autorelease()

        prev_char = chars[0]
        location = length = 0
        for idx, curr_char in enumerate(chars):
            length += 1
            if not ShChar.same_style(prev_char, curr_char):  # a group is found
                if not ShChar.same_style(prev_char, DEFAULT_CHAR):  # skip default attrs
                    attributed_text.setAttributes_range_(self._build_attributes(prev_char), (location, length - 1))
                length = 1
                location = idx
                prev_char = curr_char

            if idx == len(chars) - 1:  # last char
                if not ShChar.same_style(prev_char, DEFAULT_CHAR):
                    attributed_text.setAttributes_range_(self._build_attributes(prev_char), (location, length))

        return attributed_text

    def render(self, no_wait=False):
        """
        Render the screen buffer to the SUITextView/SUITextView_PY3. Normally the rendering process
        is delayed to throttle the total attempts of rendering.
        :param bool no_wait: Immediately render the screen without delay.
        """
        # The last_rendered_time is useful to ensure that the first rendering
        # is not delayed.
        if time() - self.last_rendered_time > self.RENDER_INTERVAL or no_wait:
            if self.render_thread is not None:
                self.render_thread.cancel()
            self._render()
        else:  # delayed rendering
            if self.render_thread is None or not self.render_thread.is_alive():
                self.render_thread = sh_delay(self._render, self.RENDER_INTERVAL)
            # Do nothing if there is already a delayed rendering thread waiting

    @on_main_thread
    def _render(self):
        # This must run on the main UI thread. Otherwise it crashes.

        self.last_rendered_time = time()

        # Lock screen to get atomic information
        with self.screen.acquire_lock():
            intact_left_bound, intact_right_bound = self.screen.get_bounds()
            screen_buffer_length = self.screen.text_length
            cursor_xs, cursor_xe = self.screen.cursor_x
            renderable_chars = self.screen.renderable_chars
            self.screen.clean()

        # Specific code for ios 8 to fix possible crash
        if ON_IOS_8:
            tvo_texts = NSMutableAttributedString.alloc().initWithAttributedString_(self.terminal.tvo.attributedText()
                                                                                    ).autorelease()
        else:
            tvo_texts = self.terminal.tso
            tvo_texts.beginEditing()  # batch the changes

        # First remove any leading texts that are rotated out
        if intact_left_bound > 0:
            tvo_texts.replaceCharactersInRange_withString_((0, intact_left_bound), '')

        tv_text_length = tvo_texts.length()

        # Second (re)render any modified trailing texts
        # When there are contents beyond the right bound, either on screen
        # or on terminal, the contents need to be re-rendered.
        if intact_right_bound < max(tv_text_length, screen_buffer_length):
            if len(renderable_chars) > 0:
                tvo_texts.replaceCharactersInRange_withAttributedString_(
                    (intact_right_bound,
                     tv_text_length - intact_right_bound),
                    self._build_attributed_string(renderable_chars)
                )
            else:  # empty string, pure deletion
                tvo_texts.replaceCharactersInRange_withString_(
                    (intact_right_bound,
                     tv_text_length - intact_right_bound),
                    ''
                )

        if ON_IOS_8:
            self.terminal.tvo.setAttributedText_(tvo_texts)  # set the text
        else:
            tvo_texts.endEditing()  # end of batched changes

        # Set the cursor position. This makes terminal and main screen cursors in sync
        self.terminal.selected_range = (cursor_xs, cursor_xe)

        # Ensure cursor line is visible by scroll to the end of the text
        self.terminal.scroll_to_end()
