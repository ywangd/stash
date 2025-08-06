# coding: utf-8
"""
Simple telent client.

usage: telnet host [-p port] [--timeout N]
"""

from __future__ import print_function
import sys
import select
import argparse
import telnetlib
import threading

from stash.system.shcommon import (
    K_CC,
    K_CD,
    K_HUP,
    K_HDN,
    K_CU,
    K_TAB,
    K_HIST,
    K_CZ,
    K_KB,
)

_SYS_STDOUT = sys.__stdout__

_stash = globals()["_stash"]
""":type : StaSh"""

try:
    import pyte
except ImportError:
    _stash("pip install pyte==0.4.10")
    import pyte


class StashTelnet(object):
    """
    Wrapper class for telnet client and pyte screen
    """

    def __init__(self):
        # Initialize the pyte screen based on the current screen size
        # noinspection PyUnresolvedReferences
        self.screen = pyte.screens.DiffScreen(*_stash.terminal.get_wh())
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.client = None

    def connect(self, host, port=23, timeout=2):
        print("Connecting...")
        try:
            self.client = telnetlib.Telnet(host, port, timeout)
            return True
        except:
            return False

    def stdout_thread(self):
        while self.running:
            # Get the list sockets which are readable
            try:
                read_sockets, write_sockets, error_sockets = select.select(
                    [self.client], [], []
                )
            except:
                break

            for sock in read_sockets:  # incoming message from remote server
                if sock == self.client:
                    rcv = sock.read_very_eager()
                    self.feed_screen(rcv)

    def feed_screen(self, data):
        """
        Feed data to the screen
        :param data: data to feed
        :type data: str
        """
        if data:
            data = data.decode("utf-8", errors="ignore")
            x, y = self.screen.cursor.x, self.screen.cursor.y
            self.stream.feed(data)
        if self.screen.dirty or x != self.screen.cursor.x or y != self.screen.cursor.y:
            self.update_screen()
            self.screen.dirty.clear()

    def update_screen(self):
        _stash.main_screen.load_pyte_screen(self.screen)
        _stash.renderer.render(no_wait=True)

    def interactive(self):
        t1 = threading.Thread(target=self.stdout_thread)
        t1.daemon = True
        self.running = True
        t1.start()
        t1.join()
        self.client.close()
        print("\nconnection closed\n")


CTRL_KEY_FLAG = 1 << 18


class SshUserActionDelegate(object):
    """
    Substitute the default user actions delegates
    """

    def __init__(self, telnet):
        self.telnet = telnet

    def send(self, s):
        # self.telnet.stream.feed(s.decode('utf-8') if hasattr(s, "decode") else s)
        self.telnet.feed_screen(s.decode("utf-8") if hasattr(s, "decode") else s)
        self.telnet.client.write(s.encode("utf-8"))


class SshTvVkKcDelegate(SshUserActionDelegate):
    """
    Delegate for TextView, Virtual keys and Key command
    """

    def textview_did_begin_editing(self, tv):
        _stash.terminal.is_editing = True

    def textview_did_end_editing(self, tv):
        _stash.terminal.is_editing = False

    def textview_should_change(self, tv, rng, replacement):
        print("SSH: tvsc: " + repr((rng, replacement)))
        # _stash.mini_buffer.feed(rng, replacement)
        if replacement == "":  # delete
            replacement = "\x08"
        # self.telnet.feed_screen(replacement)
        self.send(replacement)
        return False  # always false

    def textview_did_change(self, tv):
        pass

    def textview_did_change_selection(self, tv):
        pass

    def kc_pressed(self, key, modifierFlags):
        if modifierFlags == CTRL_KEY_FLAG:
            if key == "C":
                self.send("\x03")
                self.telnet.running = False
            elif key == "D":
                self.send("\x04")
            elif key == "A":
                self.send("\x01")
            elif key == "E":
                self.send("\x05")
            elif key == "K":
                self.send("\x0b")
            elif key == "L":
                self.send("\x0c")
            elif key == "U":
                self.send("\x15")
            elif key == "Z":
                self.send("\x1a")
            elif key == "[":
                self.send("\x1b")  # ESC
        elif modifierFlags == 0:
            if key == "UIKeyInputUpArrow":
                self.send("\x10")
            elif key == "UIKeyInputDownArrow":
                self.send("\x0e")
            elif key == "UIKeyInputLeftArrow":
                self.send("\033[D")
            elif key == "UIKeyInputRightArrow":
                self.send("\033[C")

    def vk_tapped(self, vk):
        if vk == K_TAB:
            self.send("\t")
        elif vk == K_CC:
            self.kc_pressed("C", CTRL_KEY_FLAG)
        elif vk == K_CD:
            self.kc_pressed("D", CTRL_KEY_FLAG)
        elif vk == K_CU:
            self.kc_pressed("U", CTRL_KEY_FLAG)
        elif vk == K_CZ:
            self.kc_pressed("Z", CTRL_KEY_FLAG)
        elif vk == K_HUP:
            self.kc_pressed("UIKeyInputUpArrow", 0)
        elif vk == K_HDN:
            self.kc_pressed("UIKeyInputDownArrow", 0)

        elif vk == K_KB:
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
            scrollview.superview.dx -= (
                scrollview.content_offset[0] / SshSVDelegate.SCROLL_PER_CHAR
            )
        scrollview.content_offset = (0.0, 0.0)

        offset = int(scrollview.superview.dx)
        if offset:
            scrollview.superview.dx -= offset
            if offset > 0:
                self.send("\033[C")
            else:
                self.send("\033[D")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("host", help="host to connect")
    ap.add_argument(
        "-p",
        "--port",
        action="store",
        default=23,
        type=int,
        help="port for telnet (default: 23)",
    )
    ap.add_argument("--timeout", type=int, default=2, help="timeout")
    args = ap.parse_args()

    telnet = StashTelnet()
    tv_vk_kc_delegate = SshTvVkKcDelegate(telnet)
    sv_delegate = SshSVDelegate(telnet)

    if telnet.connect(host=args.host, port=args.port, timeout=args.timeout):
        print("Connected. Press Ctrl-C to quit.")
        _stash.stream.feed("\u009bc", render_it=False)
        with _stash.user_action_proxy.config(
            tv_responder=tv_vk_kc_delegate,
            kc_responder=tv_vk_kc_delegate.kc_pressed,
            vk_responder=tv_vk_kc_delegate.vk_tapped,
            sv_responder=sv_delegate,
        ):
            telnet.interactive()
    else:
        print("Unable to connect")
