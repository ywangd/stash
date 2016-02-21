# coding: utf-8
"""
Simple telent client.

usage: telnet host [-p port] [--timeout N]
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
import sys
import select
import argparse
import telnetlib
import threading
import six

_SYS_STDOUT = sys.__stdout__

try:
    import ui
except ImportError:
    import dummyui as ui

_stash = globals()['_stash']
""":type : StaSh"""

try:
    import pyte
except ImportError:
    _stash('pip install pyte 0.4.10')


class StashTelnet(object):
    """
    Wrapper class for telnet client and pyte screen
    """

    def __init__(self):
        # Initialize the pyte screen based on the current screen size
        font_width, font_height = ui.measure_string(
            'a',
            font=('Menlo-Regular', _stash.config.getint('display', 'TEXT_FONT_SIZE')))
        # noinspection PyUnresolvedReferences
        self.screen = pyte.screens.DiffScreen(
            int(_stash.ui.width / font_width),
            int(_stash.ui.height / font_height)
        )
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.client = None

    def connect(self, host, port=23, timeout=2):
        print('Connecting...')
        try:
            self.client = telnetlib.Telnet(host, port, timeout)
            return True
        except:
            return False

    def stdout_thread(self):
        while self.running:
            # Get the list sockets which are readable
            try:
                read_sockets, write_sockets, error_sockets = select.select([self.client], [], [])
            except:
                break

            for sock in read_sockets:  # incoming message from remote server
                if sock == self.client:
                    rcv = sock.read_very_eager()
                    if rcv:
                        rcv = rcv.decode('utf-8', errors='ignore')
                        x, y = self.screen.cursor.x, self.screen.cursor.y
                        self.stream.feed(rcv)
                    if self.screen.dirty or x != self.screen.cursor.x or y != self.screen.cursor.y:
                        self.update_screen()
                        self.screen.dirty.clear()

    def update_screen(self):
        _stash.main_screen.load_pyte_screen(self.screen)
        _stash.renderer.render(no_wait=True)

    def interactive(self):
        t1 = threading.Thread(target=self.stdout_thread)
        self.running = True
        t1.start()
        t1.join()
        self.client.close()
        print('\nconnection closed\n')


CTRL_KEY_FLAG = (1 << 18)


class SshUserActionDelegate(object):
    """
    Substitute the default user actions delegates
    """
    def __init__(self, telnet):
        self.telnet = telnet

    def send(self, s):
        self.telnet.stream.feed(s if isinstance(s, six.text_type) else s.decode('utf-8'))
        self.telnet.client.write(s.encode('utf-8'))


class SshTvVkKcDelegate(SshUserActionDelegate):
    """
    Delegate for TextView, Virtual keys and Key command
    """
    def textview_did_begin_editing(self, tv):
        _stash.terminal.is_editing = True

    def textview_did_end_editing(self, tv):
        _stash.terminal.is_editing = False

    def textview_should_change(self, tv, rng, replacement):
        if replacement == '':  # delete
            replacement = '\x08'
        self.send(replacement)
        return False  # always false

    def textview_did_change(self, tv):
        pass

    def textview_did_change_selection(self, tv):
        pass

    def kc_pressed(self, key, modifierFlags):
        if modifierFlags == CTRL_KEY_FLAG:
            if key == 'C':
                self.send('\x03')
                self.telnet.running = False
            elif key == 'D':
                self.send('\x04')
            elif key == 'A':
                self.send('\x01')
            elif key == 'E':
                self.send('\x05')
            elif key == 'K':
                self.send('\x0B')
            elif key == 'L':
                self.send('\x0C')
            elif key == 'U':
                self.send('\x15')
            elif key == 'Z':
                self.send('\x1A')
            elif key == '[':
                self.send('\x1B')  # ESC
        elif modifierFlags == 0:
            if key == 'UIKeyInputUpArrow':
                self.send('\x10')
            elif key == 'UIKeyInputDownArrow':
                self.send('\x0E')
            elif key == 'UIKeyInputLeftArrow':
                self.send('\033[D')
            elif key == 'UIKeyInputRightArrow':
                self.send('\033[C')

    def vk_tapped(self, vk):
        if vk.name == 'k_tab':
            self.send('\t')
        elif vk.name == 'k_CC':
            self.kc_pressed('C', CTRL_KEY_FLAG)
        elif vk.name == 'k_CD':
            self.kc_pressed('D', CTRL_KEY_FLAG)
        elif vk.name == 'k_CU':
            self.kc_pressed('U', CTRL_KEY_FLAG)
        elif vk.name == 'k_CZ':
            self.kc_pressed('Z', CTRL_KEY_FLAG)
        elif vk.name == 'k_hup':
            self.kc_pressed('UIKeyInputUpArrow', 0)
        elif vk.name == 'k_hdn':
            self.kc_pressed('UIKeyInputDownArrow', 0)

        elif vk.name == 'k_KB':
            if _stash.terminal.is_editing:
                _stash.terminal.end_editing()
            else:
                _stash.terminal.begin_editing()


class SshSVDelegate(SshUserActionDelegate):
    """
    Delegate for scroll view
    """
    SCROLL_PER_CHAR = 20.0  # Number of pixels to scroll to move 1 character

    def scrollview_did_scroll(self, scrollview):
        # integrate small scroll motions, but keep scrollview from actually moving
        if not scrollview.decelerating:
            scrollview.superview.dx -= scrollview.content_offset[0] / SshSVDelegate.SCROLL_PER_CHAR
        scrollview.content_offset = (0.0, 0.0)

        offset = int(scrollview.superview.dx)
        if offset:
            scrollview.superview.dx -= offset
            if offset > 0:
                self.send('\033[C')
            else:
                self.send('\033[D')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('host', help='host to connect')
    ap.add_argument('-p', '--port', action='store', default=23, type=int,
                    help='port for telnet default: 23')
    ap.add_argument('--timeout', type=int, default=2,
                    help='timeout')
    args = ap.parse_args()

    telnet = StashTelnet()
    tv_vk_kc_delegate = SshTvVkKcDelegate(telnet)
    sv_delegate = SshSVDelegate(telnet)

    if telnet.connect(host=args.host, port=args.port, timeout=args.timeout):
        print('Connected. Press Ctrl-C to quit.')
        _stash.stream.feed(u'\u009bc', render_it=False)
        with _stash.user_action_proxy.config(tv_responder=tv_vk_kc_delegate,
                                             kc_responder=tv_vk_kc_delegate.kc_pressed,
                                             vk_responder=tv_vk_kc_delegate.vk_tapped,
                                             sv_responder=sv_delegate):
            telnet.interactive()
    else:
        print('Unable to connect')
