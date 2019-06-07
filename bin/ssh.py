# coding: utf-8
"""
OpenSSH client for stash.

ssh attempts to login with user provided password or looks for a valid key generated
buy ssh-keygen in ~/.ssh/
You can open an interactive shell by not passing a command. If a command is passed,
the single command is ran with output then ssh exits.

usage: ssh [-h] [--password PASSWORD] [-p PORT] host [command]

positional arguments:
  host                  host ex. user@host.com
  command               Optional command to send

optional arguments:
  -h, --help            show this help message and exit
  --password PASSWORD   Password for rsa/dsa key or password login
  -p PORT, --port PORT  port for ssh default: 22
"""
from __future__ import print_function

import argparse
import os
import sys
import threading
from distutils.version import StrictVersion

from six.moves import input

import paramiko

_SYS_STDOUT = sys.__stdout__

try:
    import ui
except ImportError:
    from . import dummyui as ui

_stash = globals()['_stash']
""":type : StaSh"""

try:
    import pyte
except ImportError:
    _stash('pip install pyte==0.4.10')

if StrictVersion(paramiko.__version__) < StrictVersion('1.15'):
    # Install paramiko 1.16.0 to fix a bug with version < 1.15
    _stash('pip install paramiko==1.16.0')
    print('Please restart Pythonista for changes to take full effect')
    sys.exit(0)


class StashSSH(object):
    """
    Wrapper class for paramiko client and pyte screen
    """

    def __init__(self):
        # Initialize the pyte screen based on the current screen size
        font_width, font_height = ui.measure_string(
            'a',
            font=('Menlo-Regular', _stash.config.getint('display', 'TEXT_FONT_SIZE')))
        # noinspection PyUnresolvedReferences
        self.screen = pyte.screens.DiffScreen(int(_stash.ui.width / font_width), int(_stash.ui.height / font_height))
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, host, passwd=None, port=22):
        print('Connecting...')
        username, host = host.split('@')

        if passwd is not None:
            return self._connect_with_passwd(host, username, passwd, port)

        else:
            print('Looking for SSH keys...')
            key_filename = self.find_ssh_keys()
            if len(key_filename) > 0:
                try:
                    self.client.connect(host, username=username, password=passwd, port=port, key_filename=key_filename)
                    return True
                except paramiko.SSHException as e:
                    print('Failed to login with SSH Keys: {}'.format(repr(e)))
                    print('Trying password ...')
                    passwd = input('Enter password:')
                    return self._connect_with_passwd(host, username, passwd, port)

                except Exception as e:
                    print('Error: {}'.format(e))
                    return False
            else:
                print('No SSH key found. Trying password ...')
                passwd = input('Enter password:')
                return self._connect_with_passwd(host, username, passwd, port)

    def _connect_with_passwd(self, host, username, passwd, port):
        try:
            self.client.connect(host, username=username, password=passwd, port=port)
            return True
        except Exception as e:
            print('Error: {}'.format(e))
            return False

    def find_ssh_keys(self):
        ssh_dir = os.path.join(os.environ['STASH_ROOT'], '.ssh')
        return [os.path.join(ssh_dir, filename) for filename in os.listdir(ssh_dir) if '.' not in filename]

    def stdout_thread(self):
        while True:
            if self.chan.recv_ready():
                rcv = self.chan.recv(4096)
                # _SYS_STDOUT.write('RRR {%s}\n' % repr(rcv))
                rcv = rcv.decode('utf-8', errors='ignore')
                x, y = self.screen.cursor.x, self.screen.cursor.y
                self.stream.feed(rcv)

                if self.screen.dirty or x != self.screen.cursor.x or y != self.screen.cursor.y:
                    self.update_screen()
                    self.screen.dirty.clear()

                if self.chan.eof_received:
                    break

    def update_screen(self):
        _stash.main_screen.load_pyte_screen(self.screen)
        _stash.renderer.render(no_wait=True)

    def single_exec(self, command):
        sin, sout, serr = self.client.exec_command(command)
        print(sout.read())
        print(serr.read())
        self.client.close()

    def interactive(self):
        self.chan = self.client.get_transport().open_session()
        self.chan.get_pty('linux', width=self.screen.columns, height=self.screen.lines)
        self.chan.invoke_shell()
        self.chan.set_combine_stderr(True)
        t1 = threading.Thread(target=self.stdout_thread)
        t1.start()
        t1.join()
        self.chan.close()
        self.client.close()
        print('\nconnection closed\n')


CTRL_KEY_FLAG = (1 << 18)


class SshUserActionDelegate(object):
    """
    Substitute the default user actions delegates
    """

    def __init__(self, ssh):
        self.ssh = ssh

    def send(self, s):
        while True:
            if self.ssh.chan.eof_received:
                break
            if self.ssh.chan.send_ready():
                # _SYS_STDOUT.write('%s, [%s]' % (rng, replacement))
                self.ssh.chan.send(s.encode('utf-8'))
                break


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
    ap.add_argument('--password', action='store', default=None, help='Password for rsa/dsa key or password login')
    ap.add_argument('-p', '--port', action='store', default=22, type=int, help='port for ssh default: 22')
    ap.add_argument('host', help='host ex. user@host.com')
    ap.add_argument('command', nargs='?', default=False, help='Command to send as a quoted string')
    args = ap.parse_args()

    ssh = StashSSH()
    tv_vk_kc_delegate = SshTvVkKcDelegate(ssh)
    sv_delegate = SshSVDelegate(ssh)

    if ssh.connect(host=args.host, passwd=args.password, port=args.port):
        print('Connected')
        if args.command:
            ssh.single_exec(args.command)
        else:
            _stash.stream.feed(u'\u009bc', render_it=False)
            with _stash.user_action_proxy.config(tv_responder=tv_vk_kc_delegate,
                                                 kc_responder=tv_vk_kc_delegate.kc_pressed,
                                                 vk_responder=tv_vk_kc_delegate.vk_tapped,
                                                 sv_responder=sv_delegate):
                ssh.interactive()
    else:
        print('Unable to connect')
