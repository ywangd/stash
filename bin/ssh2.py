# coding: utf-8
import sys
import os
import re
import time
import math
import argparse
import threading
from distutils.version import StrictVersion

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

import paramiko

if StrictVersion(paramiko.__version__) < StrictVersion('1.15'):
    # Install paramiko 1.16.0 to fix a bug with version < 1.15
    _stash('pip install paramiko 1.16.0')
    print 'Please restart Pythonista for changes to take full effect'
    sys.exit(0)


class StashSSH(object):
    def __init__(self):
        self.ssh_running = False
        font_width, font_height = ui.measure_string(
            'a',
            font=('Menlo-Regular', _stash.config.getint('display', 'TEXT_FONT_SIZE')))
        self.screen = pyte.screens.DiffScreen(
            int(_stash.ui.width / font_width),
            int(_stash.ui.height / font_height)
        )
        self.screen.dirty.clear()
        self.stream = pyte.Stream()
        self.stream.attach(self.screen)

    def connect(self, host='', passwd=None, port=22):
        print 'Connecting...'
        self.user, self.host = host.split('@')
        self.passwd = passwd
        self.port = port
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            print 'Looking for SSH keys...'
            self.ssh.connect(self.host,
                             username=self.user,
                             password=self.passwd,
                             port=self.port,
                             key_filename=self.find_ssh_keys())
        except:
            try:
                print 'No SSH key found. Trying password...'
                if self.passwd is None:
                    self.passwd = raw_input("Enter password:")

                self.ssh.connect(self.host,
                                 username=self.user,
                                 password=self.passwd,
                                 port=self.port)
            except:
                print '*Auth Error*'
                return False
        print 'Connected'
        self.ssh_running = True
        return True

    def find_ssh_keys(self):
        ssh_dir = os.path.join(os.environ['STASH_ROOT'], '.ssh')
        return [os.path.join(ssh_dir, file) for file
                in os.listdir(ssh_dir) if '.' not in file]

    def stdout_thread(self):
        while self.ssh_running:
            if self.chan.recv_ready():
                rcv = self.chan.recv(4096)

                # noinspection PyTypeChecker
                self.stream.feed(u'%s' % rcv)

                if self.screen.dirty:
                    self.update_screen()
                    self.screen.dirty.clear()

                if self.chan.eof_received:
                    # _SYS_STDOUT.write('breaking\n')
                    self.ssh_running = False
                    break

    def update_screen(self):
        _stash.main_screen.load_pyte_screen(self.screen)

        _stash.renderer.render(no_wait=True)

    def single_exec(self, command):
        sin, sout, serr = self.ssh.exec_command(command)
        for line in sout.readlines():
            line = line.replace('\n', '')
        for line in serr.readlines():
            print line.replace('\n', '')
        self.exit()

    def interactive(self):
        self.chan = self.ssh.invoke_shell()
        self.chan.set_combine_stderr(True)
        t1 = threading.Thread(target=self.stdout_thread)
        t1.start()
        t1.join()
        self.exit()

    def exit(self):
        self.ssh_running = False
        self.chan.close()
        self.ssh.close()
        print '\nconnection closed\n'


CTRL_KEY_FLAG = (1 << 18)


class SshUserActionDelegate(object):
    def __init__(self, ssh):
        self.ssh = ssh

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
        elif modifierFlags == 0:
            if key == 'UIKeyInputUpArrow':
                self.send('\x10')
            elif key == 'UIKeyInputDownArrow':
                self.send('\x0E')

    def vk_tapped(self, vk):
        if vk.name == 'k_tab':
            self.send('\t')
        elif vk.name == 'k_CC':
            self.kc_pressed('C', CTRL_KEY_FLAG)
        elif vk.name == 'k_CD':
            self.kc_pressed('D', CTRL_KEY_FLAG)
        elif vk.name == 'k_hup':
            self.kc_pressed('UIKeyInputUpArrow', 0)
        elif vk.name == 'k_hdn':
            self.kc_pressed('UIKeyInputDownArrow', 0)

        elif vk.name == 'k_KB':
            if _stash.terminal.is_editing:
                _stash.terminal.end_editing()
            else:
                _stash.terminal.begin_editing()

    def send(self, s):
        while True:
            if self.ssh.chan.eof_received:
                break
            if self.ssh.chan.send_ready():
                # _SYS_STDOUT.write('%s, [%s]' % (rng, replacement))
                self.ssh.chan.send(s)
                break


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--password', action='store', default=None,
                    help='Password for rsa/dsa key or password login')
    ap.add_argument('-p', '--port', action='store', default=22, type=int,
                    help='port for ssh default: 22')
    ap.add_argument('host', help='host ex. user@host.com')
    ap.add_argument('command', nargs='?', default=False,
                    help='Command to send as a quoted string')
    args = ap.parse_args()

    ssh = StashSSH()
    tv_delegate = SshUserActionDelegate(ssh)

    if ssh.connect(host=args.host, passwd=args.password, port=args.port):
        if args.command:
            ssh.single_exec(args.command)
        else:
            _stash.stream.feed(u'\u009bc', render_it=False)
            with _stash.user_action_proxy.config(tv_responder=tv_delegate,
                                                 kc_responder=tv_delegate.kc_pressed,
                                                 vk_responder=tv_delegate.vk_tapped):
                ssh.interactive()
    else:
        print 'Connection Failed'
