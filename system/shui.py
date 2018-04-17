# coding: utf-8
import time
import logging


try:
    import ui
except ImportError:
    from . import dummyui as ui

from .shcommon import IN_PYTHONISTA, ON_IPAD, PYTHONISTA_VERSION_LONG
from .shterminal import ShTerminal, StubTerminal

class ShVk(ui.View):
    """
    The virtual keyboard container, which implements a swipe cursor positioning gesture

    :type stash : StaSh
    """
    def __init__(self, stash, name='vks', flex='wh'):

        if not IN_PYTHONISTA:
            ui.View.__init__(self)

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


class ShUI(ui.View):
    """
    :type stash : StaSh
    """
    def __init__(self, stash, debug=False):

        self.stash = stash
        self.debug = debug
        self.logger = logging.getLogger('StaSh.UI')

        if not IN_PYTHONISTA:
            ui.View.__init__(self)

        self.is_editing = False

        self.BUFFER_MAX = stash.config.getint('display', 'BUFFER_MAX')
        self.TEXT_FONT = ('Menlo-Regular', stash.config.get('display', 'TEXT_FONT_SIZE'))
        self.BUTTON_FONT = ('Menlo-Regular', stash.config.getint('display', 'BUTTON_FONT_SIZE'))

        self.vk_symbols = stash.config.get('display', 'VK_SYMBOLS')

        # Start constructing the view's layout
        self.name = 'StaSh'
        self.flex = 'WH'
        self.background_color = 0.0

        self.txts = ui.View(name='txts', flex='WH')  # Wrapper view of output and input areas
        self.add_subview(self.txts)
        self.txts.background_color = 0.7

        # TODO: The accessory keys can be moved to a separate class
        self.vks = ShVk(stash, name='vks', flex='WT')
        self.vks.sv.delegate = self.stash.user_action_proxy.sv_delegate
        self.txts.add_subview(self.vks)
        self.vks.background_color = 0.7

        k_hspacing = 1

        self.k_tab = ui.Button(name='k_tab', title=' Tab ', flex='TB')
        self.vks.add_subview(self.k_tab)
        self.k_tab.action = self.stash.user_action_proxy.vk_tapped
        self.k_tab.font = self.BUTTON_FONT
        self.k_tab.border_width = 1
        self.k_tab.border_color = 0.9
        self.k_tab.corner_radius = 5
        self.k_tab.tint_color = 'black'
        self.k_tab.background_color = 'white'
        self.k_tab.size_to_fit()

        self.k_grp_0 = ShVk(stash, name='k_grp_0', flex='WT')  # vk group 0
        self.k_grp_0.sv.delegate = self.stash.user_action_proxy.sv_delegate
        self.vks.add_subview(self.k_grp_0)
        self.k_grp_0.background_color = 0.7
        self.k_grp_0.x = self.k_tab.width + k_hspacing

        self.k_hist = ui.Button(name='k_hist', title=' H ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hist)
        self.k_hist.action = self.stash.user_action_proxy.vk_tapped
        self.k_hist.font = self.BUTTON_FONT
        self.k_hist.border_width = 1
        self.k_hist.border_color = 0.9
        self.k_hist.corner_radius = 5
        self.k_hist.tint_color = 'black'
        self.k_hist.background_color = 'white'
        self.k_hist.size_to_fit()

        self.k_hup = ui.Button(name='k_hup', title=' Up ', flex='RTB')
        self.k_grp_0.add_subview(self.k_hup)
        self.k_hup.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_hdn.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_CD.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_CC.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_CU.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_CZ.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_KB.action = self.stash.user_action_proxy.vk_tapped
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
        self.k_swap.action = self.stash.user_action_proxy.vk_tapped
        self.k_swap.font = self.BUTTON_FONT
        self.k_swap.border_width = 1
        self.k_swap.border_color = 0.9
        self.k_swap.corner_radius = 5
        self.k_swap.tint_color = 'black'
        self.k_swap.background_color = 'white'
        self.k_swap.size_to_fit()
        self.k_swap.width -= 2
        self.k_swap.x = self.vks.width - self.k_swap.width

        self.k_grp_1 = ShVk(stash, name='k_grp_1', flex='WT')  # vk group 1
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
            k_sym.action = self.stash.user_action_proxy.vk_tapped
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

        if IN_PYTHONISTA:
            self.terminal = ShTerminal(stash,
                                       self.txts,
                                       width=self.txts.width,
                                       height=self.txts.height - (self.vks.height + 8))
        else:
            self.terminal = StubTerminal(stash)

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

    def will_close(self):
        """
        Save stuff here
        :return:
        """
        self.stash.runtime.save_history()
        self.stash.cleanup()
        # Clear the stack or the stdout becomes unusable for interactive prompt
        self.stash.runtime.worker_registry.purge()

    def toggle_k_grp(self):
        if self.on_k_grp == 0:
            self.k_grp_1.bring_to_front()
        else:
            self.k_grp_0.bring_to_front()
        self.on_k_grp = 1 - self.on_k_grp

    def history_present(self, listsource):
        table = ui.TableView()
        listsource.font = self.BUTTON_FONT
        table.data_source = listsource
        table.delegate = listsource
        table.width = 300
        table.height = 300
        table.row_height = self.BUTTON_FONT[1] + 4
        table.present('popover')
        table.wait_modal()

    def vk_tapped(self, vk):
        if vk == self.k_tab:  # Tab completion
            rng = self.terminal.selected_range
            # Valid cursor positions are only when non-selection and after the modifiable position
            if rng[0] == rng[1] and rng[0] >= self.stash.main_screen.x_modifiable:
                self.stash.mini_buffer.feed(rng, '\t')

        elif vk == self.k_swap:
            self.toggle_k_grp()

        elif vk == self.k_hist:
            self.history_present(self.stash.runtime.history_listsource)

        elif vk == self.k_hup:
            self.stash.runtime.history_up()

        elif vk == self.k_hdn:
            self.stash.runtime.history_dn()

        elif vk == self.k_CD:
            if self.stash.runtime.child_thread:
                self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_BUFFER_END, '\0')

        elif vk == self.k_CC:
            if not self.stash.runtime.child_thread:
                self.stash.write_message('no thread to terminate\n')
                self.stash.io.write(self.stash.runtime.get_prompt())

            else:  # ctrl-c terminates the entire stack of threads
                self.stash.runtime.child_thread.kill()  # this recursively kill any nested child threads
                time.sleep(0.5)  # wait a moment for the thread to terminate

        elif vk == self.k_CZ:
            self.stash.runtime.push_to_background()

        elif vk == self.k_KB:
            if self.terminal.is_editing:
                self.terminal.end_editing()
            else:
                self.terminal.begin_editing()

        elif vk == self.k_CU:
            self.stash.mini_buffer.feed(self.stash.mini_buffer.RANGE_MODIFIABLE_CHARS, '')

        elif vk.name == 'k_sym':
            self.stash.mini_buffer.feed(self.terminal.selected_range, vk.title.strip())
